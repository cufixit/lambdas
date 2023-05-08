import json
import boto3
import os

REPORTS_TABLE_NAME = os.environ["REPORTS_TABLE_NAME"]

SUBMITTED_STATUS = "SUBMITTED"
PROCESSING_STATUS = "PROCESSING"
RESOLVED_STATUS = "RESOLVED"

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    # Get the S3 bucket and object key from the event
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]

    print(f"Processing file {key} ...")

    # Download the JSON file from the S3 bucket
    s3_object = s3.get_object(Bucket=bucket, Key=key)
    s3_iterator = s3_object["Body"].iter_lines()

    # Define the DynamoDB table
    table = dynamodb.Table(REPORTS_TABLE_NAME)

    # Parse the JSON file and batch write them to DynamoDB
    entries_count = 0
    with table.batch_writer() as batch:
        for i, entry in enumerate(s3_iterator):
            if i != 0 and i % 50 == 0:
                print(f"Processed {i} entries ...")

            entry = json.loads(entry)

            if not entry["ID"].startswith("RPT-"):
                entry["ID"] = f"RPT-{entry['ID']}"
            report = {
                "ID": entry["ID"],
                "title": entry["title"],
                "building": entry["building"],
                "description": entry["description"].capitalize(),
                "createdDate": entry["createdDate"],
                "imageKeys": [],
                "userID": entry["userID"],
            }
            if keywords := entry.get("keywords"):
                report["keywords"] = set(keywords)
            if photo_labels := entry.get("photoLabels"):
                report["photoLabels"] = set(photo_labels)
            report["status"] = (
                status
                if (status := entry.get("status"))
                in [SUBMITTED_STATUS, PROCESSING_STATUS, RESOLVED_STATUS]
                else SUBMITTED_STATUS
            )
            batch.put_item(Item=report)
            entries_count += 1

    print(f"Successfully processed {entries_count} records from {key}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"Successfully processed {entries_count} records from {key}"
        ),
    }
