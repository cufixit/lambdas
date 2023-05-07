import os
import json
import boto3
from botocore.exceptions import ClientError
from apigateway_helper import cors_headers, AuthContext
from formatters import format_report, DataSource

PHOTOS_BUCKET_NAME = os.environ["PHOTOS_BUCKET_NAME"]
REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]
USER_POOL_ID = os.environ["USER_POOL_ID"]
ADMIN_POOL_ID = os.environ["ADMIN_POOL_ID"]


def allow_methods(auth_context):
    return "GET,DELETE,OPTIONS"


s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        auth_context = AuthContext(event, ADMIN_POOL_ID, USER_POOL_ID)

        reportID = event["pathParameters"]["reportId"]
        print(f"Retrieving report {reportID} ...")
        report, image_urls = get_report_by_id(reportID, auth_context)
        if report:
            return {
                "statusCode": 200,
                "headers": cors_headers(allow_methods(auth_context)),
                "body": json.dumps(
                    {
                        "report": report,
                        "images": image_urls,
                    }
                ),
            }
        return {
            "statusCode": 404,
            "headers": cors_headers(allow_methods(auth_context)),
            "body": json.dumps(f"Report {reportID} not found"),
        }

    except Exception as error:
        print(f"Error: {error}")
        return {
            "statusCode": 500,
            "headers": cors_headers("OPTIONS"),
            "body": json.dumps(f"Internal server error"),
        }


def get_report_by_id(reportID, auth_context):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
    response = reports_table.get_item(Key={"ID": reportID})

    if item := response.get("Item"):
        if auth_context.is_admin or auth_context.user_id == item["userID"]:
            report = format_report(item, DataSource.DYNAMODB, auth_context.is_admin)
            print(f"Successfully retrieved report: {report}")

            image_urls = [
                generate_presigned_url(PHOTOS_BUCKET_NAME, key)
                for key in item.get("imageKeys", [])
            ]
            print(f"Successfully retrieved presigned image URLs: {image_urls}")
            return report, image_urls

    print(f"Failed to retrieve report {reportID}: {response}")
    return None, None


def generate_presigned_url(bucket, key, expiration=3600):
    try:
        return s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiration
        )
    except ClientError as error:
        print(f"Error generating presigned URL for object {key}: {error}")
