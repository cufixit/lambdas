import os
import json
import boto3

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
PROCESS_REPORT_QUEUE_URL = os.environ["PROCESS_REPORT_QUEUE_URL"]
PROCESS_GROUP_QUEUE_URL = os.environ["PROCESS_GROUP_QUEUE_URL"]
GROUP_INDEX_NAME = os.environ["GROUP_INDEX_NAME"]

DELETE_GROUP_OPERATION = "DELETE_GROUP"
DELETE_REPORT_OPERATION = "DELETE_REPORT"
UNGROUP_REPORT_OPERATION = "UNGROUP_REPORT"


CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,DELETE,OPTIONS",
}

sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        group_id = event["pathParameters"]["groupId"]

        cascade = False
        if params := event.get("queryStringParameters"):
            cascade = params.get("cascade", "false").lower() == "true"

        reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
        items = reports_table.query(
            IndexName=GROUP_INDEX_NAME,
            KeyConditionExpression="groupID = :groupID",
            ExpressionAttributeValues={":groupID": group_id},
        ).get("Items", [])

        item_ids = [item["ID"] for item in items]
        report_ids = filter(lambda id: id.startswith("RPT-"), item_ids)
        if group_id not in item_ids:
            send_ungroup_reports_message(report_ids)
            return {
                "statusCode": 404,
                "body": json.dumps(f"Group {group_id} not found"),
            }

        send_delete_group_message(group_id)
        if cascade:
            send_delete_reports_message(report_ids)
        else:
            send_ungroup_reports_message(report_ids)

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": f"Successfully queued group for deletion",
        }

    except Exception as error:
        print(f"Error: {error}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps(f"Internal server error: {error}"),
        }


def send_delete_group_message(group_id):
    message = {
        "operation": DELETE_GROUP_OPERATION,
        "group": {"groupID": group_id},
    }
    print(f"Sending message to process-group-queue: {message}")
    response = sqs.send_message(
        QueueUrl=PROCESS_GROUP_QUEUE_URL,
        MessageBody=json.dumps(message),
    )
    print(response)


def send_delete_reports_message(report_ids):
    message = {
        "operation": DELETE_REPORT_OPERATION,
        "reports": [{"reportID": report_id} for report_id in report_ids],
    }
    print(f"Sending message to process-report-queue: {message}")
    response = sqs.send_message(
        QueueUrl=PROCESS_REPORT_QUEUE_URL,
        MessageBody=json.dumps(message),
    )
    print(response)


def send_ungroup_reports_message(report_ids):
    message = {
        "operation": UNGROUP_REPORT_OPERATION,
        "reports": [{"reportID": report_id} for report_id in report_ids],
    }
    print(f"Sending message to process-report-queue: {message}")
    response = sqs.send_message(
        QueueUrl=PROCESS_REPORT_QUEUE_URL,
        MessageBody=json.dumps(message),
    )
    print(response)
