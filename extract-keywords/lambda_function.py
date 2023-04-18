import os
import json
import boto3


comprehend = boto3.client("comprehend")
dynamodb = boto3.resource("dynamodb")


def extract_keywords(description):
    response = comprehend.detect_key_phrases(Text=description, LanguageCode="en")
    return [k["Text"] for k in response["KeyPhrases"]]


def update_report(reportID, keywords):
    reports_table = dynamodb.Table(os.environ["reportsTableName"])

    # Retrieve the existing record from DynamoDB using the report ID
    response = reports_table.get_item(Key={"reportID": reportID})
    item = response["Item"]
    print(f"Successfully retrieved item: {response}")

    if existing_keywords := item.get("keywords"):
        updated_keywords = existing_keywords.extend(keywords)
    else:
        updated_keywords = keywords

    # Update the record in DynamoDB with the new keywords
    return reports_table.update_item(
        Key={"reportID": reportID},
        UpdateExpression="SET keywords = :keywords",
        ExpressionAttributeValues={":keywords": updated_keywords},
    )


def lambda_handler(event, context):
    print(f"Received event: {event}")

    message_body = json.loads(event["Records"][0]["body"])
    reportID = message_body["reportID"]
    description = message_body["description"]

    # code adapted from https://serverlessland.com/snippets/integration-s3-to-lambda?utm_source=aws&utm_medium=link&utm_campaign=python&utm_id=docsamples
    try:
        keywords = extract_keywords(description)
        print(f"Successfully extracted keywords: {keywords}")

        response = update_report(reportID, keywords)
        print(f"Successfully updated report: {response}")

    except Exception as error:
        print(error)

    return {"statusCode": 200, "body": json.dumps("Successfully indexed photo")}
