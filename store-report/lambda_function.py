import os
import json
import boto3


INITIAL_STATUS = "CREATED"

sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")

REPORTS_TABLE_NAME = os.environ["reportsTableName"]
DETECT_KEYWORDS_QUEUE_URL = os.environ["detectKeywordsQueueUrl"]


def create_report(report_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    return reports_table.update_item(
        Key={"reportID": report_info["reportID"]},
        UpdateExpression="SET userID = :userID, title = :title, location = :location, description = :description, date = :date, imageKeys = :imageKeys, #status = :status",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":userID": report_info["userID"],
            ":title": report_info["title"],
            ":location": report_info["location"],
            ":description": report_info["description"],
            ":date": report_info["date"],
            ":imageKeys": report_info["imageKeys"],
            ":status": INITIAL_STATUS,
        },
    )


def send_to_detect_keywords_queue(report_info):
    return sqs.send_message(
        QueueUrl=DETECT_KEYWORDS_QUEUE_URL,
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
        response = create_report(report_info)
        print(f"Successfully created report in reports table: {response}")

        response = send_to_detect_keywords_queue(report_info)
        print(f"Successfully sent report to detect keywords queue: {response}")

    except Exception as error:
        print(error)

    return {"statusCode": 200, "body": json.dumps("Successfully processed report")}
