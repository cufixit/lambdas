import json
import boto3
from botocore.exceptions import ClientError
from uuid import uuid1

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

queue_url = "https://sqs.us-east-1.amazonaws.com/662545362847/NewReportText"
bucket_name = "cu-fixit-photos"


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        report = json.loads(event["body"])

        report_id = str(uuid1())
        image_keys = [f"{report_id}/{name}" for name in report["images"]]
        presigned_urls = [
            s3.generate_presigned_post(
                Bucket=bucket_name, Key=key, ExpiresIn=3600
            )
            for key in image_keys
        ]

        report_info = {
            "reportId": report_id,
            "userId": event["requestContext"]["authorizer"]["claims"]["sub"],
            "title": report["title"],
            "location": report["location"],
            "description": report["description"],
            "imageKeys": image_keys,
        }
        print(report_info)

        sqs_response = sqs.send_message(
            QueueUrl=queue_url, MessageBody=json.dumps(report_info)
        )
        print(sqs_response)

        headers = {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        }

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"reportId": report_id, "imageUrls": presigned_urls}),
        }

    except ClientError as error:
        print(error)
        return {
            "statusCode": 500,
            "body": json.dumps("An error occurred while processing the report"),
        }
