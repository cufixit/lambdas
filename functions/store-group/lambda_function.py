import os
import json
import boto3

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]

INITIAL_STATUS = "CREATED"

CREATE_GROUP_OPERATION = "CREATE_GROUP"
DELETE_GROUP_OPERATION = "DELETE_GROUP"
ADD_REPORTS_OPERATION = "ADD_REPORTS"

dynamodb = boto3.resource("dynamodb")


def create_group(group_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    response = reports_table.put_item(
        Item={
            "ID": group_info["groupID"],
            "groupID": group_info["groupID"],
            "title": group_info["title"],
            "building": group_info["building"],
            "description": group_info["description"],
            "status": INITIAL_STATUS,
        }
    )
    print(f"Successfully created group in reports table: {response}")


def delete_group(group_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    group_id = group_info["groupID"]
    print(f"Deleting group {group_id} from reports table ...")
    response = reports_table.delete_item(Key={"ID": group_id})
    if response.get("Attributes"):
        print(f"Successfully deleted group {group_id} from reports table")
    else:
        print(f"Group {group_id} not found in reports table")


def update_report_group_ids(group_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    count = 0
    for report_id in group_info["reports"]:
        try:
            reports_table.update_item(
                Key={"ID": report_id},
                UpdateExpression="SET groupID = :groupID",
                ExpressionAttributeValues={
                    ":groupID": group_info["groupID"],
                },
            )
            count += 1
        except Exception as error:
            print(f"Error updating group ID for report {report_id}: {error}")
    print(
        f"Successfully updated group IDs for {count} of {len(group_info['reports'])} reports"
    )


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        message = json.loads(event["Records"][0]["body"])
        group_info = message["group"]
        print(f"Processing {group_info} ...")

        if message["operation"] == CREATE_GROUP_OPERATION:
            create_group(group_info)
            update_report_group_ids(group_info)
        elif message["operation"] == DELETE_GROUP_OPERATION:
            delete_group(group_info)
        elif message["operation"] == ADD_REPORTS_OPERATION:
            update_report_group_ids(group_info)

    except Exception as error:
        print(error)

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"Successfully processed {message['operation']} on group {group_info['groupID']}"
        ),
    }
