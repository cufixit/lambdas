import os
import cfnresponse
from opensearchpy import OpenSearch, RequestsHttpConnection

DOMAIN_ENDPOINT = os.environ["DOMAIN_ENDPOINT"]
DOMAIN_PORT = os.environ.get("DOMAIN_PORT", 443)
MASTER_USERNAME = os.environ["MASTER_USERNAME"]
MASTER_PASSWORD = os.environ["MASTER_PASSWORD"]

CREATE = "Create"
UPDATE = "Update"

search = OpenSearch(
    hosts=[{"host": DOMAIN_ENDPOINT, "port": DOMAIN_PORT}],
    http_auth=(MASTER_USERNAME, MASTER_PASSWORD),
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)

response_data = {}


def lambda_handler(event, context):
    print(f"Received event: {event}")

    try:
        if event["RequestType"] == CREATE:
            if not search.indices.exists("reports"):
                response = search.indices.create(
                    "reports",
                    body={
                        "mappings": {
                            "properties": {
                                "reportID": {"type": "keyword"},
                                "userID": {"type": "keyword"},
                                "groupID": {"type": "keyword"},
                                "building": {"type": "keyword"},
                                "status": {"type": "keyword"},
                            }
                        }
                    },
                )
                print(f"Successfully created reports index: {response}")
            if not search.indices.exists("groups"):
                response = search.indices.create(
                    "groups",
                    body={
                        "mappings": {
                            "properties": {
                                "groupID": {"type": "keyword"},
                                "building": {"type": "keyword"},
                                "status": {"type": "keyword"},
                            }
                        }
                    },
                )
                print(f"Successfully created groups index: {response}")
        cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)

    except Exception as error:
        print(f"Error: {error}")
        cfnresponse.send(event, context, cfnresponse.FAILED, response_data)
