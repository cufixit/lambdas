import os
import json
import requests
import cfnresponse
from requests.auth import HTTPBasicAuth
from opensearchpy import OpenSearch, RequestsHttpConnection

DOMAIN_ENDPOINT = os.environ["DOMAIN_ENDPOINT"]
DOMAIN_PORT = os.environ.get("DOMAIN_PORT", 443)
MASTER_USERNAME = os.environ["MASTER_USERNAME"]
MASTER_PASSWORD = os.environ["MASTER_PASSWORD"]
ALL_ACCESS_ROLES = list(filter(None, os.environ.get("ALL_ACCESS_ROLES", []).split(",")))

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
        if event["RequestType"] == CREATE or event["RequestType"] == UPDATE:
            print("Creating reports index ...")
            create_reports_index()
            print("Creating groups index ...")
            create_groups_index()
            print(f"Assigning {ALL_ACCESS_ROLES} to all_access role ...")
            assign_all_access_roles(ALL_ACCESS_ROLES)
        print("Successfully completed all domain configurations")
        cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)

    except Exception as error:
        print(f"Failed to complete all domain configurations: {error}")
        cfnresponse.send(event, context, cfnresponse.FAILED, response_data)


def create_reports_index():
    if search.indices.exists("reports"):
        print(f"reports index already exists")
    else:
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


def create_groups_index():
    if search.indices.exists("groups"):
        print(f"groups index already exists")
    else:
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


def assign_all_access_roles(all_access_roles):
    response = requests.patch(
        f"https://{DOMAIN_ENDPOINT}:{DOMAIN_PORT}/_plugins/_security/api/rolesmapping/all_access",
        headers={"Content-Type": "application/json"},
        auth=HTTPBasicAuth(MASTER_USERNAME, MASTER_PASSWORD),
        data=json.dumps(
            [
                {
                    "op": "add",
                    "path": "/backend_roles",
                    "value": all_access_roles,
                }
            ]
        ),
    )
    print(f"Successfully assigned all access roles: {response.text}")
