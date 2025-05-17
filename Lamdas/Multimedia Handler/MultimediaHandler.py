import base64
import json
import uuid
import boto3
from boto3.dynamodb.conditions import Attr, Key
from datetime import datetime, timedelta
from decimal import Decimal

from APIRegistry import APIRouteRegistry, APIRequestException, APIServerException
import os
from botocore.exceptions import ClientError

router = APIRouteRegistry()
table_name = os.getenv("MULTIMEDIA_TABLE_NAME")
client  = boto3.client('dynamodb')
table = boto3.resource('dynamodb').Table(table_name)
s3_client = boto3.client('s3')
s3_resource = boto3.resource("s3")
s3_bucket = os.getenv("BUCKET_NAME")

@router.register_route(methods=["GET"], path="/multimedia")
def list_media(body, header, request):
    user = "projit32" #figure this out
    archive_search = request.get("queryStringParameters", {}).get("in", "").lower() == "archive"
    trash_search = request.get("queryStringParameters", {}).get("in", "").lower() == "trash"
    pagination_key = request.get("queryStringParameters", {}).get("page_id", None)
    query = {"IndexName":"TimeStampLSI",
                           "Select":"SPECIFIC_ATTRIBUTES",
                           "Limit":100,
                           "ProjectionExpression":"userName,objectName,s3Path",
                           "ScanIndexForward" :False,
                           "KeyConditionExpression":Key('userName').eq(user),
                           "FilterExpression": Attr('isTrashed').eq(trash_search) & Attr('isArchived').eq(archive_search)}

    if pagination_key:
        query['ExclusiveStartKey'] = json.loads(base64.b64decode(pagination_key.encode('utf-8')).decode('utf-8'))
        query['ExclusiveStartKey']["objectTimestamp"] = Decimal(query['ExclusiveStartKey']["objectTimestamp"])


    response = table.query(**query)
    items  = response.get("Items")
    final_response = []
    for item in items:
        final_object = {}
        final_object["objectPreSignedUrl"] = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': s3_bucket, 'Key': item["s3Path"]},
            ExpiresIn=3600,
        )
        final_object['objectName'] = item['objectName']
        final_response.append(final_object)
    api_response = {"items": final_response}


    if response.get("LastEvaluatedKey"):
        response.get("LastEvaluatedKey")["objectTimestamp"] = str(response.get("LastEvaluatedKey")["objectTimestamp"])
        api_response["page_id"] = base64.b64encode(json.dumps(response.get("LastEvaluatedKey")).encode('utf-8')).decode('utf-8')

    return api_response

@router.register_route(methods=["POST"], path="/multimedia")
def insert_media(body, header, request):
    user = "projit32"  # figure this out

    for item in body["objectDetails"]:
        item["preSignedUrl"] = create_presigned_post(s3_bucket, user+"/timeline/"+item["objectName"],
                              fields={"x-amz-meta-last-modified-datetime": item["lastModified"],
                                      "x-amz-meta-created-datetime": item['created']},
                              conditions=[{"x-amz-meta-last-modified-datetime": item["lastModified"]},
                                          {"x-amz-meta-created-datetime": item['created']}])

    return body




@router.register_route(methods=["PUT"], path="/multimedia/archive")
def archive_objects(body, header, request):
    user = "projit32"  # figure this out
    objects = body.get("items")

    response = query_table({
        "Select":"SPECIFIC_ATTRIBUTES",
        "IndexName":"TimeStampLSI",
        "ScanIndexForward":False,
        "ProjectionExpression":"userName,objectName,s3Path,isArchived,isTrashed",
        "KeyConditionExpression":Key('userName').eq(user),
        "FilterExpression":Attr('objectName').is_in(objects)
    })

    for item in response:
        destination_s3_path = user+"/archive/"+item.get("objectName")
        move_s3_object(source_key=item.get("s3Path"), destination_key=destination_s3_path)
        table.update_item(
            Key ={
                "userName": user,
                "objectName": item.get("objectName")
            },
            UpdateExpression = 'SET isArchived = :val1 , s3Path = :val2',
            ExpressionAttributeValues = {
                ":val1": True,
                ":val2": destination_s3_path
            }
        )


@router.register_route(methods=["PUT"], path="/multimedia/restore")
def restore_location(body, header, request):
    user = "projit32"  # figure this out
    objects = body.get("items")

    response = query_table({
        "Select":"SPECIFIC_ATTRIBUTES",
        "IndexName":"TimeStampLSI",
        "ScanIndexForward":False,
        "ProjectionExpression":"userName,objectName,s3Path,isArchived,isTrashed",
        "KeyConditionExpression":Key('userName').eq(user),
        "FilterExpression":Attr('objectName').is_in(objects)
    })

    for item in response:
        destination_s3_path = user+"/timeline/"+item.get("objectName")
        move_s3_object(source_key=item.get("s3Path"), destination_key=destination_s3_path)
        table.update_item(
            Key ={
                "userName": user,
                "objectName": item.get("objectName")
            },
            UpdateExpression = 'SET isArchived = :val1, isTrashed = :val1, s3Path = :val2, expiry = :val3',
            ExpressionAttributeValues = {
                ":val1": False,
                ":val2": destination_s3_path,
                ":val3": Decimal(0)
            }
        )

@router.register_route(methods=["DELETE"], path="/multimedia")
def delete_object(body, header, request):
    user = "projit32"  # figure this out
    objects = body.get("items")
    response = query_table({
        "Select":"SPECIFIC_ATTRIBUTES",
        "IndexName":"TimeStampLSI",
        "ScanIndexForward":False,
        "ProjectionExpression":"userName,objectName,s3Path,isArchived,isTrashed",
        "KeyConditionExpression":Key('userName').eq(user),
        "FilterExpression":Attr('objectName').is_in(objects)
    })
    expiration_time = int((datetime.now() + timedelta(days=30)).timestamp())

    for item in response:
        destination_s3_path = user + "/trash/" + item.get("objectName")
        move_s3_object(source_key=item.get("s3Path"), destination_key=destination_s3_path)
        table.update_item(
            Key={
                "userName": user,
                "objectName": item.get("objectName")
            },
            UpdateExpression="SET isTrashed=:val1,s3Path=:val2,expiry=:val3",
            ExpressionAttributeValues={":val1": True, ":val2":  destination_s3_path,":val3":expiration_time}
        )

def move_s3_object(source_key:str, destination_key:str):
    print("copying ", source_key, " --> ", destination_key)
    s3_resource.Object(s3_bucket, destination_key).copy({
        'Bucket': s3_bucket,
        'Key': source_key
    })

    s3_resource.Object(s3_bucket, source_key).delete()


def query_table(query_params:dict):
    response = table.query(**query_params)
    items = response.get("Items") or []

    while response.get("LastEvaluatedKey"):
        query_params["ExclusiveStartKey"] = response.get("LastEvaluatedKey")
        response = table.query(**query_params)
        items.extend(response.get("Items"))

    return items


def create_presigned_post(
    bucket_name, object_name, fields=None, conditions=None, expiration=3600
):
    """Generate a presigned URL S3 POST request to upload a file

    :param bucket_name: string
    :param object_name: string
    :param fields: Dictionary of prefilled form fields
    :param conditions: List of conditions to include in the policy
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Dictionary with the following keys:
        url: URL to post to
        fields: Dictionary of form fields and values to submit with the POST
    :return: None if error.
    """
    response = s3_client.generate_presigned_post(
        bucket_name,
        object_name,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=expiration,
    )

    # The response contains the presigned URL and required fields
    return response

def handle_request(event, context):
    try:
        return router.serve(event, context)
    except ClientError as err:
        raise APIRequestException(err.response["Error"]["Code"],
            err.response["Error"]["Message"])

    except Exception as e:
        raise APIServerException(uuid.uuid4().__str__(), e)