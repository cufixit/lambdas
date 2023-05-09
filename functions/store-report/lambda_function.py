import os
import json
import boto3

PHOTOS_BUCKET_NAME = os.environ["PHOTOS_BUCKET_NAME"]
REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
DETECT_KEYWORDS_QUEUE_URL = os.environ["DETECT_KEYWORDS_QUEUE_URL"]

SUBMITTED_STATUS = "SUBMITTED"

CREATE_REPORT_OPERATION = "CREATE_REPORT"
DELETE_REPORT_OPERATION = "DELETE_REPORT"
UPDATE_REPORT_OPERATION = "UPDATE_REPORT"
GROUP_REPORT_OPERATION = "GROUP_REPORT"
UNGROUP_REPORT_OPERATION = "UNGROUP_REPORT"

s3 = boto3.client("s3")
sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")


def create_report(report):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    response = reports_table.update_item(
        Key={"ID": report["reportID"]},
        UpdateExpression="SET userID = :userID, title = :title, building = :building, description = :description, createdDate = :createdDate, imageKeys = :imageKeys, #status = :status",
        ExpressionAttributeNames={
            "#status": "status",
        },
        ExpressionAttributeValues={
            ":userID": report["userID"],
            ":title": report["title"],
            ":building": report["building"],
            ":description": report["description"],
            ":createdDate": report["createdDate"],
            ":imageKeys": report["imageKeys"],
            ":status": SUBMITTED_STATUS,
        },
    )
    print(f"Successfully created report in reports table: {response}")
    response = sqs.send_message(
        QueueUrl=DETECT_KEYWORDS_QUEUE_URL,
        MessageBody=json.dumps(
            {
                "reportID": report["reportID"],
                "description": report["description"],
            }
        ),
    )
    print(f"Successfully sent report to detect keywords queue: {response}")


def delete_report(report):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    response = reports_table.delete_item(
        Key={"ID": report["reportID"]}, ReturnValues="ALL_OLD"
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
        print(f"Report {report['reportID']} not found in reports table")


def update_report(report):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    report_id = report["reportID"]
    print(f"Updating group {report_id} in reports table ...")
    response = reports_table.update_item(
        Key={"ID": report_id},
        UpdateExpression="SET #status = :status",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": report["status"]},
    )
    print(f"Successfully updated report {report_id} in reports table: {response}")


def group_report(report):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    report_id = report["reportID"]
    group_id = report["groupID"]
    response = reports_table.get_item(Key={"ID": group_id})
    if group := response.get("Item"):
        response = reports_table.update_item(
            Key={"ID": report_id},
            UpdateExpression="SET groupID = :groupID, #status = :status",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":groupID": group_id,
                ":status": group["status"],
            },
        )
        print(
            f"Successfully assigned report {report_id} to group {group_id}: {response}"
        )
    else:
        print(f"Group {group_id} not found in reports table")


def ungroup_report(report):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    report_id = report["reportID"]
    response = reports_table.update_item(
        Key={"ID": report_id},
        UpdateExpression="REMOVE groupID",
    )
    print(f"Successfully removed report {report_id} from group: {response}")


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        message = json.loads(event["Records"][0]["body"])
        reports = message["reports"]

        process_report = {
            CREATE_REPORT_OPERATION: create_report,
            DELETE_REPORT_OPERATION: delete_report,
            UPDATE_REPORT_OPERATION: update_report,
            GROUP_REPORT_OPERATION: group_report,
            UNGROUP_REPORT_OPERATION: ungroup_report,
        }[message["operation"]]

        for report in reports:
            process_report(report)

    except Exception as error:
        print(error)

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"Successfully processed {message['operation']} on {len(reports)} reports"
        ),
    }
