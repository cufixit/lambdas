import os
import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

AWS_REGION = os.environ["AWS_REGION"]
REPORTS_DOMAIN_HOST = os.environ["reportsDomainHost"]
REPORTS_DOMAIN_PORT = os.environ.get("reportsDomainPort", 443)

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    AWS_REGION,
    "es",
    session_token=credentials.token,
)
search = OpenSearch(
    hosts=[{"host": REPORTS_DOMAIN_HOST, "port": REPORTS_DOMAIN_PORT}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)


def lambda_handler(event, context):
    print(f"Received event: {event}")

    documents_counts = 0

    for record in event.get("Records", []):
        try:
            id = record["dynamodb"]["Keys"]["ID"]["S"]
            print(f"Updating index for record {id} ...")

            if id.startswith("GRP-"):
                if record["eventName"] == "REMOVE":
                    print(f"Removing {id} from groups index")
                    search.delete(index="groups", id=id)
                else:
                    new_image = record["dynamodb"]["NewImage"]
                    body = {
                        "groupID": id,
                        "title": new_image["title"]["S"],
                        "location": new_image["location"]["S"],
                        "description": new_image["description"]["S"],
                        "status": new_image["status"]["S"],
                    }
                    print(f"Adding {id} to groups index: {body}")
                    search.index(index="groups", id=id, body=body)

            elif id.startswith("RPT-"):
                if record["eventName"] == "REMOVE":
                    print(f"Removing {id} from reports index")
                    search.delete(index="reports", id=id)
                else:
                    new_image = record["dynamodb"]["NewImage"]
                    body = {
                        "reportID": id,
                        "userID": new_image["userID"]["S"],
                        "title": new_image["title"]["S"],
                        "location": new_image["location"]["S"],
                        "description": new_image["description"]["S"],
                        "status": new_image["status"]["S"],
                        "date": new_image["date"]["S"],
                    }
                    if "groupID" in new_image:
                        body["groupID"] = new_image["groupID"]["S"]
                    if "keywords" in new_image:
                        body["keywords"] = " ".join(new_image["keywords"]["SS"])
                    if "photoLabels" in new_image:
                        body["photoLabels"] = " ".join(new_image["photoLabels"]["SS"])
                    print(f"Adding {id} to reports index: {body}")
                    search.index(index="reports", id=id, body=body)

            documents_counts += 1

        except Exception as error:
            print(f"Error processing record: {error}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"Successfully updated or removed {documents_counts} documents"
        ),
    }
