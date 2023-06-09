import os
import json
from opensearch import opensearch

# from sklearn.feature_extraction.text import CountVectorizer
# from sklearn.decomposition import SparsePCA

AWS_REGION = os.environ["AWS_REGION"]
DOMAIN_ENDPOINT = os.environ["DOMAIN_ENDPOINT"]
DOMAIN_PORT = os.environ.get("DOMAIN_PORT", 443)

search = opensearch(AWS_REGION, DOMAIN_ENDPOINT, DOMAIN_PORT)

# s3 = boto3.client("s3")
# bucket_name = "cu-fixit-ml"
# object_key = "vocabulary.txt"

# # Load the vocabulary from the S3 bucket
# response = s3.get_object(Bucket=bucket_name, Key=object_key)
# vocab_file_content = response["Body"].read().decode("utf-8")
# vocabulary = set(vocab_file_content.split("\n"))


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
                        "building": new_image["building"]["S"],
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
                        "building": new_image["building"]["S"],
                        "description": new_image["description"]["S"],
                        "status": new_image["status"]["S"],
                        "createdDate": new_image["createdDate"]["S"],
                    }
                    if "groupID" in new_image:
                        body["groupID"] = new_image["groupID"]["S"]
                    if "keywords" in new_image:
                        body["keywords"] = " ".join(new_image["keywords"]["SS"])
                        # record_text += f", {', '.join(new_image['keywords']['SS'])}"
                    if "photoLabels" in new_image:
                        body["photoLabels"] = " ".join(new_image["photoLabels"]["SS"])
                        # record_text += f", {', '.join(new_image['photoLabels']['SS'])}"
                    print(f"Adding {id} to reports index: {body}")
                    search.index(index="reports", id=id, body=body)

                    # for attr in ["keywords", "photoLabels"]:
                    #     if attr in new_image:
                    #         words = new_image[attr]["SS"]
                    #         for word in words:
                    #             vocabulary.add(word.lower())

                    # vectorizer = CountVectorizer(vocabulary=vocabulary)
                    # # Use the existing checks to build the sequence to vectorize
                    # record_text = (
                    #     f"{new_image['title']['S']}, {new_image['building']['S']}"
                    # )

                    # X = vectorizer.fit_transform([record_text])

                    # Perform Sparse PCA on the generated vector
                    # n_components = 10
                    # sparse_pca = SparsePCA(n_components=n_components)
                    # X_reduced = sparse_pca.fit_transform(X.toarray())

                    # print(f"The vector for report {id} is {X_reduced}")
                    # TODO index the vector

            documents_counts += 1

        except Exception as error:
            print(f"Error processing record: {error}")

    # sorted_vocabulary = sorted(vocabulary)
    # vocab_file_content = "\n".join(sorted_vocabulary)
    # s3.put_object(Bucket=bucket_name, Key=object_key, Body=vocab_file_content)

    return {
        "statusCode": 200,
        "body": json.dumps(
            f"Successfully updated or removed {documents_counts} documents"
        ),
    }
