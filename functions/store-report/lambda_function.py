import os
import json
import boto3

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
DETECT_KEYWORDS_QUEUE_URL = os.environ["DETECT_KEYWORDS_QUEUE_URL"]

INITIAL_STATUS = "CREATED"

CREATE_REPORT_OPERATION = "CREATE_REPORT"

sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")


def create_report(report_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    return reports_table.update_item(
        Key={"ID": report_info["reportID"]},
        UpdateExpression="SET userID = :userID, title = :title, building = :building, description = :description, createdDate = :createdDate, imageKeys = :imageKeys, #status = :status",
        ExpressionAttributeNames={
            "#status": "status",
        },
        ExpressionAttributeValues={
            ":userID": report_info["userID"],
            ":title": report_info["title"],
            ":building": report_info["building"],
            ":description": report_info["description"],
            ":createdDate": report_info["createdDate"],
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

    try:
        message = json.loads(event["Records"][0]["body"])
        report_info = message["report"]

        if message["operation"] == CREATE_REPORT_OPERATION:
            response = create_report(report_info)
            print(f"Successfully created report in reports table: {response}")

            response = send_to_detect_keywords_queue(report_info)
            print(f"Successfully sent report to detect keywords queue: {response}")

    except Exception as error:
        print(error)

    return {
        "statusCode": 200,
        "body": json.dumps(f"Successfully processed report {report_info['reportID']}"),
    }
