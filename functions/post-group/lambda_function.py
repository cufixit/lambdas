import os
import json
import boto3
from uuid import uuid1
from botocore.exceptions import ClientError

PROCESS_GROUP_QUEUE_URL = os.environ["PROCESS_GROUP_QUEUE_URL"]
PROCESS_REPORT_QUEUE_URL = os.environ["PROCESS_REPORT_QUEUE_URL"]

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}

CREATE_GROUP_OPERATION = "CREATE_GROUP"
GROUP_REPORT_OPERATION = "GROUP_REPORT"

sqs = boto3.client("sqs")


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        body = json.loads(event["body"])

        group_id = f"GRP-{uuid1()}"
        message = {
            "operation": CREATE_GROUP_OPERATION,
            "group": {
                "groupID": group_id,
                "title": body["title"],
                "building": body["building"],
                "description": body["description"],
            },
        }

        print(f"Sending message to process-group-queue: {message}")
        response = sqs.send_message(
            QueueUrl=PROCESS_GROUP_QUEUE_URL,
            MessageBody=json.dumps(message),
        )
        print(response)

        message = {
            "operation": GROUP_REPORT_OPERATION,
            "reports": [
                {
                    "reportID": report_id,
                    "groupID": group_id,
                }
                for report_id in body["reports"]
            ],
        }
        print(f"Sending message to process-report-queue: {message}")
        response = sqs.send_message(
            QueueUrl=PROCESS_REPORT_QUEUE_URL,
            MessageBody=json.dumps(message),
        )
        print(response)

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"groupId": group_id}),
        }

    except ClientError as error:
        print(error)
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps("An error occurred while processing the group"),
        }
