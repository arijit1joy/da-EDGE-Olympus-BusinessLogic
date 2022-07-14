import json
import os
import utility as util

import boto3

LOGGER = util.get_logger(__name__)


def _invoke_lambda(function_name, query):
    lambda_client = boto3.client("lambda")

    LOGGER.debug(f"Invoking Lambda {function_name}")
    db_read_lambda_response = lambda_client.invoke(
        FunctionName=function_name, InvocationType='RequestResponse', LogType='None',
        Payload=bytes(json.dumps(query).encode("utf-8"))
    )

    # Decode and return the lambda's response
    return json.loads(db_read_lambda_response["Payload"].read().decode("utf-8"))


def invoke_db_reader(read_query):
    edge_db_reader_name = os.environ["EDGEDBReader_ARN"]

    LOGGER.debug("Invoking the EDGE DB Reader Lambda . . .")

    return _invoke_lambda(edge_db_reader_name, read_query)


def invoke_db_common_api(write_query):
    edge_common_api_name = os.environ["EDGECommonDBAPI_ARN"]

    LOGGER.debug("Invoking the EDGE DB Common API Lambda . . .")

    return _invoke_lambda(edge_common_api_name, write_query)