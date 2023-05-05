import os
import json
import boto3
from botocore.exceptions import ClientError
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

CORS_HEADERS = {
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}

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

dynamodb = boto3.resource("dynamodb")

REPORTS_TABLE_NAME = os.environ["reportsTableName"]


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        groupID = event["pathParameters"].get("groupId")
        print(f"Retrieving similar reports for group {groupID} ...")

        reports_table = dynamodb.Table(REPORTS_TABLE_NAME)
        response = reports_table.get_item(Key={"ID": groupID})
        print(f"Successfully retrieved group: {response}")

        if not (item := response.get("Item")):
            return {
                "statusCode": 404,
                "headers": CORS_HEADERS,
                "body": json.dumps(f"Group {groupID} not found"),
            }

        query_string = item["title"]

        response = search.search(
            index="reports",
            body={
                "query": {
                    "bool": {
                        "should": {
                            "multi_match": {
                                "query": query_string,
                                "fields": [
                                    "title^4",
                                    "keywords^2",
                                    "photoLabels^2",
                                    "location",
                                    "description",
                                ],
                            }
                        },
                        "must_not": {"exists": {"field": "groupID"}},
                    }
                }
            },
        )
        print(f"Successfully retrieved reports from OpenSearch: {response}")

        suggested_reports = [
            hit["_source"] for hit in response["hits"]["hits"] if "_source" in hit
        ]

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(suggested_reports),
        }

    except ClientError as error:
        print(error)
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps("An error occurred while suggesting reports"),
        }
