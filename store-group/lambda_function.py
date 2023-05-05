import os
import json
import boto3


INITIAL_STATUS = "CREATED"

dynamodb = boto3.resource("dynamodb")

REPORTS_TABLE_NAME = os.environ["reportsTableName"]


def create_group(group_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    return reports_table.put_item(
        Item={
            "ID": group_info["groupID"],
            "groupID": group_info["groupID"],
            "title": group_info["title"],
            "location": group_info["location"],
            "description": group_info["description"],
            "status": INITIAL_STATUS,
        }
    )


def update_report_group_ids(group_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    count = 0
    for reportID in group_info["reports"]:
        try:
            reports_table.update_item(
                Key={"ID": reportID},
                UpdateExpression="SET groupID = :groupID",
                ExpressionAttributeValues={
                    ":groupID": group_info["groupID"],
                },
            )
            count += 1
        except Exception as error:
            print(f"Error updating group ID for report {reportID}: {error}")
    return count


def lambda_handler(event, context):
    print(f"Received event: {event}")
    message = event["Records"][0]["body"]
    group_info = json.loads(message)

    try:
        response = create_group(group_info)
        print(f"Successfully created group in reports table: {response}")

        count = update_report_group_ids(group_info)
        print(
            f"Successfully updated group IDs for {count} of {len(group_info['reports'])} reports"
        )

    except Exception as error:
        print(error)

    return {
        "statusCode": 200,
        "body": json.dumps(f"Successfully processed group {group_info['groupID']}"),
    }
