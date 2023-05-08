import os
import json
import boto3

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
PROCESS_REPORT_QUEUE_URL = os.environ["PROCESS_REPORT_QUEUE_URL"]

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "PUT,OPTIONS",
}

GROUP_REPORT_OPERATION = "GROUP_REPORT"

sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        body = json.loads(event["body"])
        group_id = event["pathParameters"]["groupId"]

        if len(body["reports"]) == 0:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps("No reports were provided"),
            }

        reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
        response = reports_table.get_item(Key={"ID": group_id})
        if not response.get("Item"):
            return {
                "statusCode": 404,
                "headers": CORS_HEADERS,
                "body": json.dumps(f"Group {group_id} not found"),
            }

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
            "body": json.dumps("Successfully queued reports for grouping"),
        }

    except Exception as error:
        print(error)
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps("Internal server error"),
        }
