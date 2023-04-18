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


def update_report(reportID, labels):
    reports_table = dynamodb.Table(os.environ["reportsTableName"])

    # Retrieve the existing record from DynamoDB using the report ID
    response = reports_table.get_item(Key={"reportID": reportID})
    item = response["Item"]
    print(f"Successfully retrieved item: {response}")

    if existing_labels := item.get("photo_labels"):
        updated_labels = existing_labels.extend(labels)
    else:
        updated_labels = labels

    # Update the record in DynamoDB with the new labels
    return reports_table.update_item(
        Key={"reportID": reportID},
        UpdateExpression="SET photo_labels = :labels",
        ExpressionAttributeValues={":labels": updated_labels},
    )


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
        """
        response = s3.head_object(Bucket=bucket_name, Key=object_key)
        custom_labels = []
        if response["Metadata"]:
            print("METADATA IS:", response["Metadata"])

            if response["Metadata"]['customlabels']:
                json_labels = json.loads(response["Metadata"]['customlabels'])
                to_append = json_labels['labels']
                print("the custom labels are:", to_append)
                custom_labels = to_append


        print("The custom labels are", custom_labels)
        """

        labels = extract_photo_labels(bucket_name, object_key)
        print(f"Successfully extracted labels: {labels}")

        response = update_report(reportID, labels)
        print(f"Successfully updated report: {response}")

    except Exception as error:
        print(error)

    return {"statusCode": 200, "body": json.dumps("Successfully indexed photo")}
