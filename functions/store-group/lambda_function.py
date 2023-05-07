import os
import json
import boto3

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]

INITIAL_STATUS = "CREATED"

CREATE_GROUP_OPERATION = "CREATE_GROUP"
ADD_REPORTS_OPERATION = "ADD_REPORTS"

dynamodb = boto3.resource("dynamodb")


def create_group(group_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    return reports_table.put_item(
        Item={
            "ID": group_info["groupID"],
            "groupID": group_info["groupID"],
            "title": group_info["title"],
            "building": group_info["building"],
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

    try:
        message = json.loads(event["Records"][0]["body"])
        group_info = message["group"]

        if message["operation"] == CREATE_GROUP_OPERATION:
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
