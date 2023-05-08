import os
import json
import boto3

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]

INITIAL_STATUS = "CREATED"

CREATE_GROUP_OPERATION = "CREATE_GROUP"
DELETE_GROUP_OPERATION = "DELETE_GROUP"

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


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        message = json.loads(event["Records"][0]["body"])
        group_info = message["group"]
        print(f"Processing {group_info} ...")

        if message["operation"] == CREATE_GROUP_OPERATION:
            create_group(group_info)
        elif message["operation"] == DELETE_GROUP_OPERATION:
            delete_group(group_info)

    except Exception as error:
        print(error)

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"Successfully processed {message['operation']} on group {group_info['groupID']}"
        ),
    }
