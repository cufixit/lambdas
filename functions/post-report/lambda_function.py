import os
import json
import boto3
from uuid import uuid1
from datetime import datetime
from botocore.exceptions import ClientError

PHOTOS_BUCKET_NAME = os.environ["PHOTOS_BUCKET_NAME"]
PROCESS_REPORT_QUEUE_URL = os.environ["PROCESS_REPORT_QUEUE_URL"]

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}

CREATE_REPORT_OPERATION = "CREATE_REPORT"

s3 = boto3.client("s3")
sqs = boto3.client("sqs")


def generate_presigned_post(bucket, report_id, images, expiration=3600):
    image_keys = [f"{report_id}/{name}" for name in images]
    presigned_urls = [
        s3.generate_presigned_post(Bucket=bucket, Key=key, ExpiresIn=expiration)
        for key in image_keys
    ]
    return image_keys, presigned_urls


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        body = json.loads(event["body"])
        userID = event["requestContext"]["authorizer"]["claims"]["sub"]

        # generate presigned URLs to post images
        reportID = f"RPT-{uuid1()}"
        image_keys, presigned_urls = generate_presigned_post(
            bucket=PHOTOS_BUCKET_NAME,
            report_id=reportID,
            images=body["images"],
        )

        # generate create report message
        message = {
            "operation": CREATE_REPORT_OPERATION,
            "report": {
                "reportID": reportID,
                "userID": userID,
                "title": body["title"],
                "building": body["building"],
                "description": body["description"],
                "createdDate": datetime.now().strftime("%m/%d/%Y"),
                "imageKeys": image_keys,
            },
        }
        print(f"Sending message to process-report-queue: {message}")

        # send create report message to SQS queue
        response = sqs.send_message(
            QueueUrl=PROCESS_REPORT_QUEUE_URL,
            MessageBody=json.dumps(message),
        )
        print(response)

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"reportId": reportID, "imageUrls": presigned_urls}),
        }

    except ClientError as error:
        print(error)
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps("An error occurred while processing the report"),
        }
