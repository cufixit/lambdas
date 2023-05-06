import os
import json
import boto3
from uuid import uuid1
from datetime import datetime
from botocore.exceptions import ClientError

PROCESS_GROUP_QUEUE_URL = os.environ["PROCESS_GROUP_QUEUE_URL"]

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}

sqs = boto3.client("sqs")


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        body = json.loads(event["body"])

        if event["resource"] == "/groups":
            groupID = f"GRP-{uuid1()}"
            message = {
                "operation": "CREATE_REPORT",
                "group": {
                    "groupID": groupID,
                    "title": body["title"],
                    "location": body["location"],
                    "description": body["description"],
                    "reports": body["reports"],
                },
            }

        elif event["resource"] == "/groups/{groupId}/reports":
            groupID = event["pathParameters"]["groupId"]
            if len(body["reports"]) == 0:
                return {
                    "statusCode": 400,
                    "headers": CORS_HEADERS,
                    "body": json.dumps("No reports were provided"),
                }
            message = {
                "operation": "ADD_REPORTS",
                "group": {
                    "groupID": groupID,
                    "reports": body["reports"],
                },
            }

        print(f"Sending message to process-group-queue: {message}")
        response = sqs.send_message(
            QueueUrl=PROCESS_GROUP_QUEUE_URL,
            MessageBody=json.dumps(message),
        )
        print(response)

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"groupId": groupID}),
        }

    except ClientError as error:
        print(error)
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps("An error occurred while processing the group"),
        }
