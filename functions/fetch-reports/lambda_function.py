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
            report, image_urls = get_report_by_id(reportID, is_admin, userID)
            if report:
                return {
                    "statusCode": 200,
                    "headers": CORS_HEADERS,
                    "body": json.dumps(
                        {
                            "report": report,
                            "images": image_urls,
                        }
                    ),
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
                from_param=int(query.get("from", 0)),
                size_param=min(int(query.get("size", 20)), 25),
                userID=userID,
                query_string=query.get("q"),
                filter_userID=query.get("userId"),
                filter_building=query.get("building"),
                filter_status=query.get("status"),
            )
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(
                    {
                        "reports": reports,
                    }
                ),
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
            report = format_report(item, is_admin, DataSource.DYNAMODB)
            print(f"Successfully retrieved report: {report}")
            image_urls = [
                generate_presigned_url(PHOTOS_BUCKET_NAME, key)
                for key in item.get("imageKeys", [])
            ]
            print(f"Successfully retrieved presigned image URLs: {image_urls}")
            return report, image_urls

    print(f"Failed to retrieve report {reportID}: {response}")
    return None


def get_filtered_reports(
    is_admin,
    from_param,
    size_param,
    userID=None,
    query_string=None,
    filter_userID=None,
    filter_building=None,
    filter_status=None,
):
    must_clauses = []
    if not is_admin:
        must_clauses.append({"term": {"userID": userID}})
    elif filter_userID:
        must_clauses.append({"term": {"userID": filter_userID}})
    if filter_building:
        must_clauses.append({"term": {"building": filter_building}})
    if filter_status:
        must_clauses.append({"term": {"status": filter_status}})

    should_clauses = []
    if query_string:
        should_clauses.append(
            {
                "multi_match": {
                    "query": query_string,
                    "fields": [
                        "title^4",
                        "keywords^4",
                        "photoLabels^2",
                        "building^2",
                        "description",
                    ],
                }
            }
        )

    response = search.search(
        index="reports",
        body={
            "from": from_param,
            "size": size_param,
            "query": {"bool": {"must": must_clauses, "should": should_clauses}},
        },
    )
    print(f"Successfully queried reports: {response}")
    return [
        format_report(hit["_source"], is_admin, DataSource.OPENSEARCH)
        for hit in response["hits"]["hits"]
    ]


def format_report(item, is_admin, data_source):
    if data_source == DataSource.DYNAMODB:
        item["reportID"] = item.pop("ID")
    if keywords := item.get("keywords"):
        item["keywords"] = (
            keywords.split(" ")
            if data_source == DataSource.OPENSEARCH
            else list(keywords)
        )
    if photo_labels := item.get("photoLabels"):
        item["photo_labels"] = (
            photo_labels.split(" ")
            if data_source == DataSource.OPENSEARCH
            else list(photo_labels)
        )
    report = {
        "reportId": item["reportID"],
        "userId": item["userID"],
        "title": item["title"],
        "building": item["building"],
        "description": item["description"],
        "createdDate": item["created_date"],
        "status": item["status"],
        "keywords": item.get("keywords"),
        "photoLabels": item.get("photo_labels"),
    }
    if is_admin:
        report["groupId"] = item.get("groupID")
    return report


def generate_presigned_url(bucket, key, expiration=3600):
    try:
        return s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiration
        )
    except ClientError as error:
        print(f"Error generating presigned URL for object {key}: {error}")
