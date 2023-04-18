import os
import json
import boto3
import urllib.parse

s3 = boto3.client("s3")
rekognition = boto3.client("rekognition")
dynamodb = boto3.resource("dynamodb")


def extract_photo_labels(bucket_name, object_key):
    response = rekognition.detect_labels(
        Image={"S3Object": {"Bucket": bucket_name, "Name": object_key}}
    )
    return [l["Name"] for l in response["Labels"]]


def create_or_update_report(reportID, labels):
    reports_table = dynamodb.Table(os.environ["reportsTableName"])

    # Retrieve the existing record from DynamoDB using the report ID
    response = reports_table.get_item(Key={"reportID": reportID})
    print(f"Fetching report {reportID} from table: {response}")

    if item := response.get("Item"):
        # If record already exists, append the labels
        print(f"Successfully fetched report: {item}")
        if existing_labels := item.get("photo_labels"):
            labels = existing_labels.extend(labels)
        return reports_table.update_item(
            Key={"reportID": reportID},
            UpdateExpression="SET photo_labels = :labels",
            ExpressionAttributeValues={":labels": labels},
        )
    else:
        # If record does not exist, create a new record with the labels
        print(f"Report with ID {reportID} not found")
        table_item = {
            "reportID": reportID,
            "photo_labels": labels,
        }
        print(f"Putting report in table: {table_item}")
        return reports_table.put_item(Item=table_item)


def lambda_handler(event, context):
    print(f"Received event: {event}")

    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    object_key = urllib.parse.unquote_plus(
        event["Records"][0]["s3"]["object"]["key"], encoding="utf-8"
    )

    # key_name should be in form {reportID}/{image_name} so split on '/' to get reportID
    reportID = object_key.split("/")[0]
    image_name = object_key.split("/")[1]
    print(f"Processing image {image_name} for report {reportID}")

    # code adapted from https://serverlessland.com/snippets/integration-s3-to-lambda?utm_source=aws&utm_medium=link&utm_campaign=python&utm_id=docsamples
    try:
        labels = extract_photo_labels(bucket_name, object_key)
        print(f"Successfully extracted labels: {labels}")

        response = create_or_update_report(reportID, labels)
        print(f"Successfully updated report: {response}")

    except Exception as error:
        print(error)

    return {"statusCode": 200, "body": json.dumps("Successfully indexed photo")}