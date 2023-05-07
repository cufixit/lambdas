import os
import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from apigateway_helper import cors_headers, AuthContext
from reports_helper import format_report, DataSource

AWS_REGION = os.environ["AWS_REGION"]
DOMAIN_ENDPOINT = os.environ["DOMAIN_ENDPOINT"]
DOMAIN_PORT = os.environ.get("DOMAIN_PORT", 443)
USER_POOL_ID = os.environ["USER_POOL_ID"]
ADMIN_POOL_ID = os.environ["ADMIN_POOL_ID"]

DEFAULT_SIZE = 20
MAX_SIZE = 25


def allow_methods(auth_context):
    if auth_context.is_admin:
        return "GET,OPTIONS"
    return "GET,POST,OPTIONS"


credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    AWS_REGION,
    "es",
    session_token=credentials.token,
)
search = OpenSearch(
    hosts=[{"host": DOMAIN_ENDPOINT, "port": DOMAIN_PORT}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        auth_context = AuthContext(event, ADMIN_POOL_ID, USER_POOL_ID)

        params = p if (p := event.get("queryStringParameters")) else {}
        print(f"Retrieving reports with query params {params} ...")

        reports = get_filtered_reports(
            auth_context,
            page_from=int(params.get("from", 0)),
            page_size=min(int(params.get("size", DEFAULT_SIZE)), MAX_SIZE),
            query=params.get("q"),
            user_id=params.get("userId"),
            building=params.get("building"),
            status=params.get("status"),
        )

        return {
            "statusCode": 200,
            "headers": cors_headers(allow_methods(auth_context)),
            "body": json.dumps(
                {
                    "reports": reports,
                }
            ),
        }

    except Exception as error:
        print(f"Error: {error}")
        return {
            "statusCode": 500,
            "headers": cors_headers("OPTIONS"),
            "body": json.dumps(f"Internal server error"),
        }


def get_filtered_reports(
    auth_context,
    page_from=None,
    page_size=None,
    query=None,
    user_id=None,
    building=None,
    status=None,
):
    must_clauses = []
    if not auth_context.is_admin:
        must_clauses.append({"term": {"userID": auth_context.user_id}})
    elif user_id:
        must_clauses.append({"term": {"userID": user_id}})
    if building:
        must_clauses.append({"term": {"building": building}})
    if status:
        must_clauses.append({"term": {"status": status}})

    should_clauses = []
    if query:
        should_clauses.append(
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^4",
                        "keywords^4",
                        "photoLabels^2",
                        "building^2",
                        "description",
                    ],
                }
            }
        )

    response = search.search(
        index="reports",
        body={
            "from": page_from if page_from else 0,
            "size": page_size if page_size else DEFAULT_SIZE,
            "query": {"bool": {"must": must_clauses, "should": should_clauses}},
        },
    )
    print(f"Successfully queried reports: {response}")
    return [
        format_report(hit["_source"], auth_context, DataSource.OPENSEARCH)
        for hit in response["hits"]["hits"]
    ]
