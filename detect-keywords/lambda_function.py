import os
import json
import boto3
import inflect

p = inflect.engine()

comprehend = boto3.client("comprehend")
dynamodb = boto3.resource("dynamodb")


def detect_keywords(description):
    response = comprehend.detect_key_phrases(Text=description, LanguageCode="en")

    def normalize(word):
        word = word.lower().strip()
        return singular if (singular := p.singular_noun(word)) else word

    return [
        normalize(kw) for kp in response["KeyPhrases"] for kw in kp["Text"].split(" ")
    ]


def update_report(reportID, keywords):
    reports_table = dynamodb.Table(os.environ["reportsTableName"])

    # Update the record in DynamoDB with the new keywords
    return reports_table.update_item(
        Key={"ID": reportID},
        UpdateExpression="SET keywords = :keywords",
        ExpressionAttributeValues={":keywords": set(keywords)},
    )


def lambda_handler(event, context):
    print(f"Received event: {event}")

    message_body = json.loads(event["Records"][0]["body"])
    reportID = message_body["reportID"]
    description = message_body["description"]

    try:
        keywords = detect_keywords(description)
        print(f"Detected keywords: {keywords}")

        response = update_report(reportID, keywords)
        print(f"Successfully updated report: {response}")

    except Exception as error:
        print(error)

    return {"statusCode": 200, "body": json.dumps("Successfully extracted keywords")}
