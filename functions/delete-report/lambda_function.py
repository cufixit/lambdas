import os
import json
import boto3
from apigateway_helper import cors_headers, AuthContext

PHOTOS_BUCKET_NAME = os.environ["PHOTOS_BUCKET_NAME"]
REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
USER_POOL_ID = os.environ["USER_POOL_ID"]
ADMIN_POOL_ID = os.environ["ADMIN_POOL_ID"]


s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


def allow_methods(auth_context):
    return "GET,DELETE,OPTIONS"


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        auth_context = AuthContext(event, ADMIN_POOL_ID, USER_POOL_ID)

        report_id = event["pathParameters"]["reportId"]
        print(f"Deleting report {report_id} ...")

        deleted_item = delete_report(report_id, auth_context)
        if not deleted_item:
            return {
                "statusCode": 404,
                "headers": cors_headers(allow_methods(auth_context)),
                "body": json.dumps(f"Report {report_id} not found"),
            }

        if image_keys := deleted_item.get("imageKeys", []):
            response = delete_images(image_keys)
            print(f"Succesfully deleted photos from S3: {response}")

        return {
            "statusCode": 200,
            "headers": cors_headers(allow_methods(auth_context)),
        }

    except Exception as error:
        print(f"Error: {error}")
        return {
            "statusCode": 500,
            "headers": cors_headers("OPTIONS"),
            "body": json.dumps(f"Internal server error"),
        }


def delete_report(reportID, auth_context):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    try:
        if auth_context.is_admin:
            response = reports_table.delete_item(
                Key={"ID": reportID}, ReturnValues="ALL_OLD"
            )
        else:
            response = reports_table.delete_item(
                Key={"ID": reportID},
                ReturnValues="ALL_OLD",
                ConditionExpression="userId = :userId",
                ExpressionAttributeValues={":userId": auth_context.user_id},
            )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException as error:
        print(f"Error: {error}")
        response = {}

    if item := response.get("Attributes"):
        print(f"Successfully deleted report: {item}")
        return item
    return None


def delete_images(image_keys):
    return s3.delete_objects(
        Bucket=PHOTOS_BUCKET_NAME,
        Delete={"Objects": [{"Key": key} for key in image_keys]},
    )
