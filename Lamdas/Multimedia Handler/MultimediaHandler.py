import uuid
import boto3
from APIRegistry import APIRouteRegistry, APIRequestException, APIServerException
import os
from botocore.exceptions import ClientError

router = APIRouteRegistry()
table_name = os.getenv("TABLE_NAME")
client  = boto3.client('dynamodb')
table = boto3.resource('dynamodb').Table(table_name)

@router.register_route(methods=["GET"], path="/multimedia")
def list_media(body, header, request):
    user = "" #figure this out


def handle_request(event, context):
    try:
        return router.serve(event, context)
    except ClientError as err:
        raise APIRequestException(err.response["Error"]["Code"],
            err.response["Error"]["Message"])

    except Exception as e:
        raise APIServerException(uuid.uuid4().__str__(), e)