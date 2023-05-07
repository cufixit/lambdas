import os
import json
import boto3
from botocore.exceptions import ClientError
from formatters import format_group, format_group_report, DataSource

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
GROUP_INDEX_NAME = os.environ["GROUP_INDEX_NAME"]

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,DELETE,OPTIONS",
}

dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        groupID = event["pathParameters"]["groupId"]
        print(f"Retrieving group {groupID} ...")

        group, reports = get_group_by_id(groupID)
        if group:
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(
                    {
                        "group": group,
                        "reports": reports,
                    }
                ),
            }
        return {
            "statusCode": 404,
            "headers": CORS_HEADERS,
            "body": json.dumps(f"Group {groupID} not found"),
        }

    except Exception as error:
        print(f"Error: {error}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps(f"Internal server error"),
        }


def get_group_by_id(groupID):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    response = reports_table.get_item(Key={"ID": groupID})

    if item := response.get("Item"):
        group = format_group(item, DataSource.DYNAMODB)
        print(f"Successfully retrieved group: {group}")

        response = reports_table.query(
            IndexName=GROUP_INDEX_NAME,
            KeyConditionExpression="groupID = :groupID",
            ExpressionAttributeValues={
                ":groupID": groupID,
            },
        )
        reports = [
            format_group_report(item, DataSource.DYNAMODB)
            for item in response.get("Items", [])
            if item["ID"].startswith("RPT-")
        ]
        print(f"Successfully retrieved reports: {group}")
        return group, reports

    print(f"Failed to retrieve report {groupID}: {response}")
    return None, None
