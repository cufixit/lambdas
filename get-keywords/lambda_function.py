import json
import boto3

# based on HW2 index-photos
REGION = "us-east-1"
TABLE = "MaintenanceReports"

session = boto3.Session()


def update_report(reportID, new_labels):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE)

    # Retrieve the existing record from DynamoDB using the report ID
    response = table.get_item(Key={"reportID": reportID})
    item = response["Item"]
    print(f"Successfully got item: {response}")
    # Extract the existing labels from the record
    # Right now this will be an empty set, possible it will be pre-populated later
    if item.get("keywords"):
        existing_labels = item.get("keywords")

        # Add the new labels to the existing set
        updated_labels = existing_labels.append(new_labels)
    else:
        updated_labels = new_labels

    # Update the record in DynamoDB with the new labels
    update = table.update_item(
        Key={"reportID": reportID},
        UpdateExpression="SET keywords = :labels",
        ExpressionAttributeValues={":labels": updated_labels},
    )

    print(f"The table updated successfully: {update}")


def lambda_handler(event, context):
    s3_client = boto3.client("s3")
    comp_client = boto3.client("comprehend")
    txt = json.loads(event["Records"][0]["body"])
    reportID = txt["reportID"]
    description = txt["description"]

    # code adapted from https://serverlessland.com/snippets/integration-s3-to-lambda?utm_source=aws&utm_medium=link&utm_campaign=python&utm_id=docsamples
    try:
        # use detect_keywords
        label_response = comp_client.detect_key_phrases(
            Text=description, LanguageCode="en"
        )

        # build list of only the labels from the response
        # try to do set compression not sure if it'll work
        labels = [k["Text"] for k in label_response["KeyPhrases"]]
        """
        labels = []
        for l in label_response["Labels"]:
            labels.append(l['Name'])
        """
        print("the Comprehend labels are", labels)

        update_report(reportID, labels)

    except Exception as e:
        print(e)
        print(
            "Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.".format(
                key_name, bucket
            )
        )
        raise e

    return {"statusCode": 200, "body": json.dumps("Successfully indexed photo")}
