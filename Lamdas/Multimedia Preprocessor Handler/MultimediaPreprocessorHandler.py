import os
import mimetypes
import json
import urllib.parse
import boto3
from datetime import datetime, timezone
from pymediainfo import MediaInfo
from decimal import Decimal

os.environ["MULTIMEDIA_TABLE_NAME"] = "multimedia-datastore"
table = boto3.resource('dynamodb').Table(os.getenv("MULTIMEDIA_TABLE_NAME"))
s3 = boto3.client('s3')
def get_file_type(file_path: str) -> tuple[str | None, str | None]:
    return mimetypes.guess_type(file_path)

def get_info(path:str) -> (dict, dict):
    mime_type = get_file_type(path)[0]
    media_info = MediaInfo.parse(path)
    meta_data = dict()
    info = media_info.general_tracks[0].__dict__
    if mime_type.startswith("image/"):
        meta_data = media_info.image_tracks[0].__dict__

    if mime_type.startswith("video/"):
        meta_data = media_info.video_tracks[0].__dict__

    return meta_data, info


def dump_into_database(data: dict, info:dict, meta_data:dict):
    table.put_item(Item={
        **data,
        "info": info,
        "metadata": meta_data
    })
    print("Data Inserted in DB")

def get_signed_url(bucket: str, obj: str, expires_in=300):
    """
    Generate a signed URL
    :param expires_in:  URL Expiration time in seconds
    :param bucket:
    :param obj:         S3 Key name
    :return:            Signed URL
    """
    presigned_url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': obj}, ExpiresIn=expires_in)
    return presigned_url

def handler(event, context):

    # For debugging so you can see raw event format.
    print('Here is the event:')
    print((json.dumps(event)))

    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    url = get_signed_url(bucket, key)

    metadata, info = get_info(url)
    print("Object Info: ", info, "Object Metadata", metadata)

    object_metadata = s3.head_object(Bucket=bucket, Key=key).get("Metadata")
    print("S3 Object metadata: ",object_metadata)

    data = {
        "userName" : key.split("/")[0],
        "objectName": key.split("/")[-1],
        "s3Path": key,
        "uploadedTimestamp": Decimal(datetime.now(timezone.utc).timestamp()),
        "objectTimestamp": Decimal(datetime.fromisoformat(object_metadata['last-modified-datetime'].replace(" UTC", "Z")).timestamp()),
        "isArchived": False,
        "isTrashed": False
    }
    dump_into_database(data, info, metadata)