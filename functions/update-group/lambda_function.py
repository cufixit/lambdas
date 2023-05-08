import os
import json
import boto3

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
PROCESS_REPORT_QUEUE_URL = os.environ["PROCESS_REPORT_QUEUE_URL"]
PROCESS_GROUP_QUEUE_URL = os.environ["PROCESS_GROUP_QUEUE_URL"]
GROUP_INDEX_NAME = os.environ["GROUP_INDEX_NAME"]

UPDATE_GROUP_OPERATION = "UPDATE_GROUP"
UPDATE_REPORT_OPERATION = "UPDATE_REPORT"
UNGROUP_REPORT_OPERATION = "UNGROUP_REPORT"

SUBMITTED_STATUS = "SUBMITTED"
PROCESSING_STATUS = "PROCESSING"
RESOLVED_STATUS = "RESOLVED"

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,PATCH,DELETE,OPTIONS",
}

sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        group_id = event["pathParameters"]["groupId"]

        reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
        items = reports_table.query(
            IndexName=GROUP_INDEX_NAME,
            KeyConditionExpression="groupID = :groupID",
            ExpressionAttributeValues={":groupID": group_id},
        ).get("Items", [])

        group, reports = None, []
        for item in items:
            if item["ID"].startswith("GRP-"):
                group = item
            elif item["ID"].startswith("RPT-"):
                reports.append(item)

        if not group:
            send_ungroup_reports_message([report["ID"] for report in reports])
            return {
                "statusCode": 404,
                "body": json.dumps(f"Group {group_id} not found"),
            }

        body = json.loads(event["body"])
        status = body.get("status")
        if status not in [SUBMITTED_STATUS, PROCESSING_STATUS, RESOLVED_STATUS]:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps(f"Invalid status: {status}"),
            }

        if group["status"] != status:
            send_update_group_message(group_id, status)
        else:
            print(f"Group {group_id} already has status {status}")

        report_ids = [report["ID"] for report in reports if report["status"] != status]
        if report_ids:
            send_update_reports_message(report_ids, status)
        else:
            print(f"All reports in group {group_id} already have status {status}")

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": f"Successfully queued group and reports for status update",
        }

    except Exception as error:
        print(f"Error: {error}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps(f"Internal server error"),
        }


def send_update_group_message(group_id, status):
    message = {
        "operation": UPDATE_GROUP_OPERATION,
        "group": {"groupID": group_id, "status": status},
    }
    print(f"Sending message to process-group-queue: {message}")
    response = sqs.send_message(
        QueueUrl=PROCESS_GROUP_QUEUE_URL,
        MessageBody=json.dumps(message),
    )
    print(response)


def send_update_reports_message(report_ids, status):
    message = {
        "operation": UPDATE_REPORT_OPERATION,
        "reports": [
            {"reportID": report_id, "status": status} for report_id in report_ids
        ],
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
