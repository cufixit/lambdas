import os
import json
import boto3
import urllib.parse
import inflect

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]

dynamodb = boto3.resource("dynamodb")
rekognition = boto3.client("rekognition")
s3 = boto3.client("s3")

p = inflect.engine()


def detect_photo_labels(bucket_name, object_key):
    response = rekognition.detect_labels(
        Image={"S3Object": {"Bucket": bucket_name, "Name": object_key}},
        MaxLabels=5,
    )

    def normalize(word):
        word = word.lower().strip()
        return singular if (singular := p.singular_noun(word)) else word

    return [normalize(lw) for l in response["Labels"] for lw in l["Name"].split(" ")]


def update_report(reportID, photo_labels):
    reports_table = dynamodb.Table(REPORTS_TABLE_NAME)

    # Update the record in DynamoDB with the new photo labels
    return reports_table.update_item(
        Key={"ID": reportID},
        UpdateExpression="ADD photoLabels :photoLabels",
        ExpressionAttributeValues={":photoLabels": set(photo_labels)},
    )


def lambda_handler(event, context):
    print(f"Received event: {event}")

    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    object_key = urllib.parse.unquote_plus(
        event["Records"][0]["s3"]["object"]["key"], encoding="utf-8"
    )

    # key_name should be in form {reportID}/{image_name}
    reportID = object_key.split("/")[0]
    image_name = object_key.split("/")[1]
    print(f"Processing image {image_name} for report {reportID}")

    try:
        photo_labels = detect_photo_labels(bucket_name, object_key)
        print(f"Detected photo labels: {photo_labels}")

        response = update_report(reportID, photo_labels)
        print(f"Successfully updated report: {response}")

    except Exception as error:
        print(error)

    return {
        "statusCode": 200,
        "body": json.dumps("Successfully extracted photo labels"),
    }
