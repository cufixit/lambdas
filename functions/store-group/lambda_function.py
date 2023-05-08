import os
import json
import boto3

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]

SUBMITTED_STATUS = "SUBMITTED"

CREATE_GROUP_OPERATION = "CREATE_GROUP"
DELETE_GROUP_OPERATION = "DELETE_GROUP"
UPDATE_GROUP_OPERATION = "UPDATE_GROUP"

dynamodb = boto3.resource("dynamodb")


def create_group(group):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    response = reports_table.put_item(
        Item={
            "ID": group["groupID"],
            "groupID": group["groupID"],
            "title": group["title"],
            "building": group["building"],
            "description": group["description"],
            "status": SUBMITTED_STATUS,
        }
    )
    print(f"Successfully created group in reports table: {response}")


def delete_group(group):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    group_id = group["groupID"]
    print(f"Deleting group {group_id} from reports table ...")
    response = reports_table.delete_item(Key={"ID": group_id})
    if response.get("Attributes"):
        print(f"Successfully deleted group {group_id} from reports table")
    else:
        print(f"Group {group_id} not found in reports table")


def update_group(group):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    group_id = group["groupID"]
    print(f"Updating group {group_id} in reports table ...")
    response = reports_table.update_item(
        Key={"ID": group_id},
        UpdateExpression="SET #status = :status",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": group["status"]},
    )
    print(f"Successfully updated group {group_id} in reports table: {response}")


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        message = json.loads(event["Records"][0]["body"])
        group = message["group"]
        print(f"Processing {group} ...")

        if message["operation"] == CREATE_GROUP_OPERATION:
            create_group(group)
        elif message["operation"] == DELETE_GROUP_OPERATION:
            delete_group(group)
        elif message["operation"] == UPDATE_GROUP_OPERATION:
            update_group(group)

    except Exception as error:
        print(error)

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"Successfully processed {message['operation']} on group {group['groupID']}"
        ),
    }
