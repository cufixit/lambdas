from enum import Enum


class DataSource(Enum):
    DYNAMODB = "dynamodb"
    OPENSEARCH = "opensearch"


def format_report(item, data_source, is_admin):
    if data_source == DataSource.DYNAMODB:
        item["reportID"] = item.pop("ID")
    if keywords := item.get("keywords"):
        item["keywords"] = (
            keywords.split(" ")
            if data_source == DataSource.OPENSEARCH
            else list(keywords)
        )
    if photo_labels := item.get("photoLabels"):
        item["photo_labels"] = (
            photo_labels.split(" ")
            if data_source == DataSource.OPENSEARCH
            else list(photo_labels)
        )
    report = {
        "reportId": item["reportID"],
        "userId": item["userID"],
        "title": item["title"],
        "building": item["building"],
        "description": item["description"],
        "createdDate": item["createdDate"],
        "status": item["status"],
        "keywords": item.get("keywords"),
        "photoLabels": item.get("photo_labels"),
    }
    if is_admin:
        report["groupId"] = item.get("groupID")
    return report


def format_group(item, data_source):
    if data_source == DataSource.DYNAMODB:
        item["groupID"] = item.pop("ID")
    group = {
        "groupId": item["groupID"],
        "title": item["title"],
        "building": item["building"],
        "description": item["description"],
        "status": item["status"],
    }
    return group
