import os
import re
import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from botocore.exceptions import ClientError
from inflection import singularize


CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}

credentials = boto3.Session().get_credentials()
service = "es"
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    os.environ["AWS_REGION"],
    service,
    session_token=credentials.token,
)
search = OpenSearch(
    hosts=[{"host": os.environ["reportsDomainEndpoint"], "port": 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


def generate_presigned_url(bucket, object_key, expiration=3600):
    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=expiration,
        )
    except ClientError as error:
        print(error)


def query(keywords):
    # keywords = clean_keywords(keywords) Don't clean for now because you aren't storing as lowercase in dynamo
    print("Cleaned up keywords:", keywords)

    q = {"size": 100, "query": {"multi_match": {"query": keywords}}}

    response = search.search(index="reports", body=q)
    print(f"Received response: {response}")

    hits = response["hits"]["hits"]
    return [hit["_source"]["reportID"] for hit in hits]


def clean_keywords(keywords):
    keywords = [
        part.strip()
        for keyword in keywords
        for part in re.sub(r"(?: and | in | the | a )", ",", keyword).split(",")
    ]
    keywords = list(filter(bool, keywords))
    keywords = [re.sub(r"\s+", "", keyword) for keyword in keywords]
    keywords = [keyword.lower() for keyword in keywords]
    keywords = [singularize(keyword) for keyword in keywords]

    return keywords


def get_all_reports():
    reports_table = dynamodb.Table(os.environ["reportsTableName"])

    response = reports_table.scan()
    if items := response.get("Items"):
        while last_evaluated_key := response.get("LastEvaluatedKey"):
            response = reports_table.scan(ExclusiveStartKey=last_evaluated_key)
            items.extend(response["Items"])
        print(f"Successfully retrieved items: {items}")
        return items
    
    print(f"Failed to retrieve items: {response}")
    return []


def get_report_by_id(reportID):
    reports_table = dynamodb.Table(os.environ["reportsTableName"])

    response = reports_table.get_item(Key={"reportID": reportID})
    if item := response.get("Item"):
        item["imageUrls"] = [
            generate_presigned_url(os.environ["photosBucketName"], key)
            for key in item.get("imageKeys", [])
        ]
        print(f"Successfully retrieved item: {item}")
        return item
    
    print(f"Failed to retrieve item: {response}")
    return None


# TODO modify update_report to update based on the given flag
# For now it only sets the status to "REVIEWED"
def update_report(reportID, to_update="REVIEWED", flag="status"):
    table = dynamodb.Table(os.environ["reportsTableName"])

    # Retrieve the existing record from DynamoDB using the report ID
    response = table.get_item(Key={"reportID": reportID})
    item = response["Item"]
    # print(f"Successfully got item: {response}")
    # Extract the existing set of labels from the record
    # Right now this will be an empty set, possible it will be pre-populated later
    cur_status = item.get("status")

    # Update the record in DynamoDB with the new labels
    update = table.update_item(
        Key={"reportID": reportID},
        UpdateExpression="SET #status = :status",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": to_update},
    )

    # print(f"The table updated successfully: {update}")


def lambda_handler(event, context):
    print(f"Received event: {event}")
    # user_query = event.get("q")

    reportID = None
    if path_params := event["pathParameters"]:
        reportID = path_params.get("reportId")

    try:
        results = []
        if reportID:
            # user_query = reportID
            # dynamoIDs = query(
            #     user_query
            # )  # this is returning multiple results because of the way I was generating test cases based on timestamp
            # print(f"The dynamoIDs are: {dynamoIDs}")

            if report := get_report_by_id(reportID):
                print(f"Successfully retrieved report: {report}")
                results.append(report)
        else:
            print("About to scan dynamo")
            results.extend(get_all_reports())

        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(results)}

    except Exception as error:
        print(error)
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps("Backend error"),
        }
