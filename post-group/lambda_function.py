import os
import json
import boto3
from uuid import uuid1
from datetime import datetime
from botocore.exceptions import ClientError

sqs = boto3.client("sqs")

PROCESS_GROUP_QUEUE_URL = os.environ["processGroupQueueUrl"]

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        # parse group information from event
        group = json.loads(event["body"])
        groupID = f"GRP-{uuid1()}"

        # generate SQS message containing group content
        group["reports"] = group.get("reports", [])
        if not isinstance(group["reports"], list):
            group["reports"] = [group["reports"]]

        group_info = {
            "groupID": groupID,
            "title": group["title"],
            "location": group["location"],
            "description": group["description"],
            "reports": group["reports"],
        }
        print(group_info)

        # send report content to SQS queue
        sqs_response = sqs.send_message(
            QueueUrl=PROCESS_GROUP_QUEUE_URL,
            MessageBody=json.dumps(group_info),
        )
        print(sqs_response)

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
            "body": json.dumps("An error occurred while processing the report"),
        }
