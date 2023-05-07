import os
import json
import boto3

PHOTOS_BUCKET_NAME = os.environ["PHOTOS_BUCKET_NAME"]
REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
DETECT_KEYWORDS_QUEUE_URL = os.environ["DETECT_KEYWORDS_QUEUE_URL"]

INITIAL_STATUS = "CREATED"

CREATE_REPORT_OPERATION = "CREATE_REPORT"
DELETE_REPORT_OPERATION = "DELETE_REPORT"
UNGROUP_REPORT_OPERATION = "UNGROUP_REPORT"

s3 = boto3.client("s3")
sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")


def create_report(report_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    response = reports_table.update_item(
        Key={"ID": report_info["reportID"]},
        UpdateExpression="SET userID = :userID, title = :title, building = :building, description = :description, createdDate = :createdDate, imageKeys = :imageKeys, #status = :status",
        ExpressionAttributeNames={
            "#status": "status",
        },
        ExpressionAttributeValues={
            ":userID": report_info["userID"],
            ":title": report_info["title"],
            ":building": report_info["building"],
            ":description": report_info["description"],
            ":createdDate": report_info["createdDate"],
            ":imageKeys": report_info["imageKeys"],
            ":status": INITIAL_STATUS,
        },
    )
    print(f"Successfully created report in reports table: {response}")
    response = sqs.send_message(
        QueueUrl=DETECT_KEYWORDS_QUEUE_URL,
        MessageBody=json.dumps(
            {
                "reportID": report_info["reportID"],
                "description": report_info["description"],
            }
        ),
    )
    print(f"Successfully sent report to detect keywords queue: {response}")


def delete_report(report_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    response = reports_table.delete_item(
        Key={"ID": report_info["reportID"]}, ReturnValues="ALL_OLD"
    )
    if deleted_item := response.get("Attributes"):
        print(f"Successfully deleted report from reports table: {deleted_item}")
        if image_keys := deleted_item.get("imageKeys", []):
            response = s3.delete_objects(
                Bucket=PHOTOS_BUCKET_NAME,
                Delete={"Objects": [{"Key": key} for key in image_keys]},
            )
            print(f"Succesfully deleted {len(image_keys)} photos from S3: {response}")
    else:
        print(f"Report {report_info['reportID']} not found in reports table")


def ungroup_report(report_info):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    response = reports_table.update_item(
        Key={"ID": report_info["reportID"]},
        UpdateExpression="REMOVE groupID",
    )
    print(f"Successfully ungrouped report in reports table: {response}")


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        message = json.loads(event["Records"][0]["body"])
        reports = message["reports"]

        if message["operation"] == CREATE_REPORT_OPERATION:
            for report_info in reports:
                create_report(report_info)
        elif message["operation"] == DELETE_REPORT_OPERATION:
            for report_info in reports:
                delete_report(report_info)
        elif message["operation"] == UNGROUP_REPORT_OPERATION:
            for report_info in reports:
                ungroup_report(report_info)

    except Exception as error:
        print(error)

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"Successfully processed {message['operation']} on {len(reports)} reports"
        ),
    }
