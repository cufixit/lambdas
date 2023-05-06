import os
import json
import boto3
from enum import Enum
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

AWS_REGION = os.environ["AWS_REGION"]
PHOTOS_BUCKET_NAME = os.environ["PHOTOS_BUCKET_NAME"]
REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
DOMAIN_ENDPOINT = os.environ["DOMAIN_ENDPOINT"]
DOMAIN_PORT = os.environ.get("DOMAIN_PORT", 443)
USER_POOL_ID = os.environ["USER_POOL_ID"]
ADMIN_POOL_ID = os.environ["ADMIN_POOL_ID"]

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    AWS_REGION,
    "es",
    session_token=credentials.token,
)
search = OpenSearch(
    hosts=[{"host": DOMAIN_ENDPOINT, "port": DOMAIN_PORT}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)


class DataSource(Enum):
    DYNAMODB = "dynamodb"
    OPENSEARCH = "opensearch"


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        authorizer = event["requestContext"]["authorizer"]
        userID = authorizer["claims"]["sub"]
        user_pool_id = authorizer["claims"]["iss"].split("/")[-1]

        if user_pool_id not in [ADMIN_POOL_ID, USER_POOL_ID]:
            return {
                "statusCode": 403,
                "headers": CORS_HEADERS,
                "body": json.dumps(f"Not authorized to access this resource"),
            }
        is_admin = user_pool_id == ADMIN_POOL_ID

        if event["resource"] == "/reports/{reportId}":
            reportID = event["pathParameters"]["reportId"]
            print(f"Retrieving report {reportID} ...")
            if report := get_report_by_id(reportID, is_admin, userID):
                return {
                    "statusCode": 200,
                    "headers": CORS_HEADERS,
                    "body": json.dumps(report),
                }
            return {
                "statusCode": 404,
                "headers": CORS_HEADERS,
                "body": json.dumps(f"Report {reportID} not found"),
            }

        elif event["resource"] == "/reports":
            query = params if (params := event["queryStringParameters"]) else {}
            print(f"Retrieving reports with query params {query} ...")
            reports = get_filtered_reports(
                is_admin,
                from_param=query.get("from", 0),
                size_param=query.get("size", 20),
                userID=userID,
                filter_userID=query.get("userId"),
                filter_building=query.get("building"),
                filter_status=query.get("status"),
            )
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(reports),
            }

    except Exception as error:
        print(f"Error: {error}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps(f"Internal server error"),
        }


def get_report_by_id(reportID, is_admin, userID=None):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    response = reports_table.get_item(Key={"ID": reportID})

    if item := response.get("Item"):
        if is_admin or userID == item["userId"]:
            report = format_report(item, DataSource.DYNAMODB, include_image_urls=True)
            print(f"Successfully retrieved report: {report}")
            return report

    print(f"Failed to retrieve report {reportID}: {response}")
    return None


def get_filtered_reports(
    is_admin,
    from_param,
    size_param,
    userID=None,
    filter_userID=None,
    filter_building=None,
    filter_status=None,
):
    must_clauses = []
    if not is_admin:
        must_clauses.append({"term": {"userID": userID}})
    if filter_userID and is_admin:
        must_clauses.append({"term": {"userID": filter_userID}})
    if filter_building:
        must_clauses.append({"term": {"building": filter_building}})
    if filter_status:
        must_clauses.append({"term": {"status": filter_status}})

    response = search.search(
        index="reports",
        body={
            "from": from_param,
            "size": size_param,
            "query": {"bool": {"must": must_clauses}},
        },
    )
    print(f"Successfully queried reports: {response}")
    return [
        format_report(hit["_source"], DataSource.OPENSEARCH)
        for hit in response["hits"]["hits"]
    ]


def format_report(item, data_source, include_image_urls=False):
    if data_source == DataSource.OPENSEARCH:
        if keywords := item.get("keywords"):
            item["keywords"] = keywords.split(" ")
        if photo_labels := item.get("photoLabels"):
            item["photoLabels"] = photo_labels.split(" ")
    elif data_source == DataSource.DYNAMODB:
        item["reportID"] = item["ID"]
        if keywords := item.get("keywords"):
            item["keywords"] = list(keywords)
        if photo_labels := item.get("photoLabels"):
            item["photoLabels"] = list(photo_labels)
    report = {
        "reportId": item["reportID"],
        "userId": item["userID"],
        "title": item["title"],
        "building": item["building"],
        "description": item["description"],
        "createdDate": item["created_date"],
        "status": item["status"],
        "groupId": item.get("groupID"),
        "keywords": item.get("keywords"),
        "photoLabels": item.get("photoLabels"),
    }
    if data_source == DataSource.DYNAMODB and include_image_urls:
        report["imageUrls"] = [
            generate_presigned_url(PHOTOS_BUCKET_NAME, key)
            for key in item.get("imageKeys", [])
        ]
    return report


def generate_presigned_url(bucket, key, expiration=3600):
    try:
        return s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiration
        )
    except ClientError as error:
        print(f"Error generating presigned URL for object {key}: {error}")
