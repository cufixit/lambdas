import os
import json
import boto3
from uuid import uuid1
from datetime import datetime
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

PHOTOS_BUCKET_NAME = os.environ["photosBucketName"]
PROCESS_REPORT_QUEUE_URL = os.environ["processReportQueueUrl"]

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


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
        # parse report and user information from event
        report = json.loads(event["body"])
        userID = event["requestContext"]["authorizer"]["claims"]["sub"]

        # generate presigned URLs to post images
        reportID = f"RPT-{uuid1()}"
        image_keys, presigned_urls = generate_presigned_post(
            bucket=PHOTOS_BUCKET_NAME,
            report_id=reportID,
            images=report["images"],
        )

        # generate SQS message containing report content
        report_info = {
            "reportID": reportID,
            "userID": userID,
            "title": report["title"],
            "location": report["location"],
            "description": report["description"],
            "date": datetime.now().strftime("%m/%d/%Y"),
            "imageKeys": image_keys,
        }
        print(report_info)

        # send report content to SQS queue
        sqs_response = sqs.send_message(
            QueueUrl=PROCESS_REPORT_QUEUE_URL,
            MessageBody=json.dumps(report_info),
        )
        print(sqs_response)

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
