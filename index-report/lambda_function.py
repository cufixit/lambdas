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

    reports_count = 0

    try:
        for record in event.get("Records", []):
            id = record["dynamodb"]["Keys"]["reportID"]["S"]
            if record["eventName"] == "REMOVE":
                print(f"Removing report {id} from reports index")
                search.delete(index="reports", id=id)
            else:
                body = record["dynamodb"]["NewImage"]
                print(f"Adding report {id} to reports index: {body}")
                search.index(index="reports", id=id, body=body)
            reports_count += 1

    except Exception as error:
        print(error)

    return {
        "statusCode": 200,
        "body": json.dumps(f"Successfully indexed {reports_count} reports"),
    }
