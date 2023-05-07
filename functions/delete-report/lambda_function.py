import os
import json
import boto3
from apigateway_helper import cors_headers, AuthContext

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
PROCESS_REPORT_QUEUE_URL = os.environ["PROCESS_REPORT_QUEUE_URL"]
USER_POOL_ID = os.environ["USER_POOL_ID"]
ADMIN_POOL_ID = os.environ["ADMIN_POOL_ID"]

DELETE_REPORT_OPERATION = "DELETE_REPORT"


s3 = boto3.client("s3")
sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")


def allow_methods(auth_context):
    return "GET,DELETE,OPTIONS"


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        auth_context = AuthContext(event, ADMIN_POOL_ID, USER_POOL_ID)
        report_id = event["pathParameters"]["reportId"]

        reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
        user_id = (
            reports_table.get_item(Key={"ID": report_id}).get("Item", {}).get("userID")
        )
        if not user_id:
            return {
                "statusCode": 404,
                "headers": cors_headers(allow_methods(auth_context)),
                "body": json.dumps(f"Report {report_id} not found"),
            }
        if auth_context.is_admin or auth_context.user_id == user_id:
            message = {
                "operation": DELETE_REPORT_OPERATION,
                "reports": [{"reportID": report_id}],
            }
            print(f"Sending message to process-report-queue: {message}")
            response = sqs.send_message(
                QueueUrl=PROCESS_REPORT_QUEUE_URL,
                MessageBody=json.dumps(message),
            )
            print(response)
            return {
                "statusCode": 200,
                "headers": cors_headers(allow_methods(auth_context)),
                "body": f"Successfully queued report deletion",
            }
        else:
            return {
                "statusCode": 403,
                "headers": cors_headers(allow_methods(auth_context)),
                "body": json.dumps(f"Not authorized"),
            }

    except Exception as error:
        print(f"Error: {error}")
        return {
            "statusCode": 500,
            "headers": cors_headers("OPTIONS"),
            "body": json.dumps(f"Internal server error"),
        }
