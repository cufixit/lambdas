import os
import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth


INITIAL_STATUS = "CREATED"

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

sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")


def put_report(report_info):
    reports_table = dynamodb.Table(os.environ["reportsTableName"])

    # Retrieve the existing record from DynamoDB using the report ID
    response = reports_table.get_item(Key={"reportID": report_info["reportID"]})
    print(f"Fetching report {report_info['reportID']} from table: {response}")

    photo_labels = None
    if item := response.get("Item"):
        # If record already exists, fetch the existing labels
        print(f"Successfully fetched report: {item}")
        photo_labels = item.get("photo_labels")
    else:
        print(f"Report with ID {report_info['reportID']} not found")

    table_item = {
        "reportID": report_info["reportID"],
        "userID": report_info["userID"],
        "title": report_info["title"],
        "location": report_info["location"],
        "description": report_info["description"],
        "date": report_info["date"],
        "imageKeys": report_info["imageKeys"],
        "status": INITIAL_STATUS,
        "photo_labels": photo_labels,
        "keywords": None,
    }
    print(f"Putting report in table: {table_item}")
    return reports_table.put_item(Item=table_item)


def index_report(report_info):
    index_body = {
        "reportID": report_info["reportID"],
        "userID": report_info["userID"],
        "title": report_info["title"],
        "location": report_info["location"],
        "description": report_info["description"],
        "date": report_info["date"],
        "status": INITIAL_STATUS,
    }
    print(f"Adding report to index: {index_body}")
    return search.index(index="reports", id=report_info["reportID"], body=index_body)


def send_report_to_keyword_extraction_queue(report_info):
    return sqs.send_message(
        QueueUrl=os.environ["keywordExtractionQueueUrl"],
        MessageBody=json.dumps(
            {
                "reportID": report_info["reportID"],
                "description": report_info["description"],
            }
        ),
    )


def lambda_handler(event, context):
    print(f"Received event: {event}")
    message = event["Records"][0]["body"]
    report_info = json.loads(message)

    try:
        response = put_report(report_info)
        print(f"Successfully put report in table: {response}")

        response = index_report(report_info)
        print(f"Successfully added report to index: {response}")

        response = send_report_to_keyword_extraction_queue(report_info)
        print(f"Successfully sent report to keyword queue: {response}")

    except Exception as error:
        print(error)

    return {"statusCode": 200, "body": json.dumps("Successfully processed report")}
