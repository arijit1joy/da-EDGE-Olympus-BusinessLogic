import os
import shutil
from geopy.distance import distance
from datetime import datetime
from behave import given, then
from pypika import Table, Query, Order
from utilities import rest_api_utility as rest_api
from utilities.db_utility import get_edge_db_payload
from utilities.common_utility import exception_handler
from utilities.file_utility.file_handler import same_file_contents
from utilities.aws_utilities.s3_utility import get_key_from_list_of_s3_objects, download_object_from_s3, \
    delete_object_from_s3

DOWNLOAD_FOLDER_PATH = "data/j1939_hb/download"


@exception_handler
@given(u'A valid EBU HB message in JSON format containing a valid data')
def valid_ebu_hb_message(context):
    context.j1939_hb_stages = ["FILE_RECEIVED", "CD_PT_POSTED", "FILE_SENT"]
    context.download_converted_file_name = "data/j1939_hb/download/received_j1939_hb_ebu_converted_file.json"
    context.compare_converted_file_name = "data/j1939_hb/compare/j1939_hb_ebu_converted_file.json"
    context.download_ngdi_file_name = "data/j1939_hb/download/received_j1939_hb_ebu_ngdi_file.json"
    context.compare_ngdi_file_name = "data/j1939_hb/compare/j1939_hb_ebu_ngdi_file.json"
    context.device_id = context.ebu_device_id_1
    context.esn = context.ebu_esn_1


@exception_handler
@given(u'A valid EBU HB message in JSON format containing a device ID that does not exist in the EDGE ecosystem')
def valid_ebu_hb_message_with_not_exist_device(context):
    context.j1939_hb_stages = ["FILE_RECEIVED"]
    context.download_converted_file_name = \
        "data/j1939_hb/download/received_j1939_hb_ebu_converted_file_device_does_not_exist.json"
    context.compare_converted_file_name = \
        "data/j1939_hb/compare/j1939_hb_ebu_converted_file_device_does_not_exist.json"
    context.device_id = context.not_whitelisted_device_id
    context.esn = context.ebu_esn_1


@exception_handler
@given(u'An invalid EBU HB message in JSON format containing a valid deviceID but missing the telematicsPartnerName '
       u'and customerReference')
def valid_ebu_hb_message_without_tpn_and_cr(context):
    context.j1939_hb_stages = []
    context.download_converted_file_name = \
        "data/j1939_hb/download/received_j1939_hb_ebu_converted_file_without_tpn_and_cr.json"
    context.compare_converted_file_name = \
        "data/j1939_hb/compare/j1939_hb_ebu_converted_file_without_tpn_and_cr.json"
    context.download_ngdi_file_name = "data/j1939_hb/download/received_j1939_hb_ebu_ngdi_file_without_tpn_and_cr.json"
    context.compare_ngdi_file_name = "data/j1939_hb/compare/j1939_hb_ebu_ngdi_file_without_tpn_and_cr.json"
    context.device_id = context.ebu_device_id_2
    context.esn = context.ebu_esn_2


@exception_handler
@given(u'An invalid EBU HB message in JSON format containing a valid deviceID but having incorrect values for the '
       u'telematicsPartnerName and customerReference')
def valid_ebu_hb_message_incorrect_tpn_and_cr(context):
    context.j1939_hb_stages = ["FILE_RECEIVED", "CD_PT_POSTED", "FILE_SENT"]
    context.download_converted_file_name = \
        "data/j1939_hb/download/received_j1939_hb_ebu_converted_file_incorrect_tpn_and_cr.json"
    context.compare_converted_file_name = \
        "data/j1939_hb/compare/j1939_hb_ebu_converted_file_incorrect_tpn_and_cr.json"
    context.download_ngdi_file_name = \
        "data/j1939_hb/download/received_j1939_hb_ebu_ngdi_file_incorrect_tpn_and_cr.json"
    context.compare_ngdi_file_name = "data/j1939_hb/compare/j1939_hb_ebu_ngdi_file_incorrect_tpn_and_cr.json"
    context.device_id = context.ebu_device_id_3
    context.esn = context.ebu_esn_3


@exception_handler
@given(u'A valid PSBU HB message in JSON format containing a valid data')
def valid_psbu_hb_message(context):
    context.j1939_hb_stages = ["FILE_RECEIVED", "FILE_SENT"]
    context.download_converted_file_name = "data/j1939_hb/download/received_j1939_hb_psbu_converted_file.json"
    context.compare_converted_file_name = "data/j1939_hb/compare/j1939_hb_psbu_converted_file.json"
    context.device_id = context.psbu_device_id_1
    context.esn = context.psbu_esn_1


@exception_handler
@then(u'Stored J1939 HB metadata stages in EDGE DB')
def assert_j1939_hb_stages_in_edge_db(context):
    da_edge_metadata = Table(context.edge_metadata_table)
    query = Query.from_(da_edge_metadata).select(da_edge_metadata.data_pipeline_stage).where(
        da_edge_metadata.device_id == context.device_id).where(da_edge_metadata.data_protocol == "J1939_HB")  # noqa
    edge_db_payload = get_edge_db_payload('get', query)
    edge_db_response = rest_api.post(context.edge_common_db_url, edge_db_payload)
    received_stages = [stage["data_pipeline_stage"] for stage in edge_db_response["body"]]
    assert set(context.j1939_hb_stages) == set(received_stages)


@exception_handler
@then(u'Obfuscate GPS Co-Ordinates and Stored in Device Health Data')
def assert_j1939_hb_obfuscate_gps_coordinates_in_edge_db(context):
    device_health_data = Table(context.device_health_data_table)
    converted_device_params = context.j1939_hb_payload["samples"][0]["convertedDeviceParameters"]
    message_id = converted_device_params["messageID"]
    latitude, longitude = converted_device_params["Latitude"], converted_device_params["Longitude"]
    query = Query.from_(device_health_data).select(device_health_data.latitude, device_health_data.longitude).where(
        device_health_data.device_id == context.device_id).where(  # noqa
        device_health_data.health_param_message_id == message_id).orderby(  # noqa
        device_health_data.device_health_sn, order=Order.desc)
    edge_db_payload = get_edge_db_payload('get', query)
    edge_db_response = rest_api.post(context.edge_common_db_url, edge_db_payload)

    # Asserting obfuscate gps co-ordinates stored in device health data table
    edge_db_response_body = edge_db_response["body"][0]
    stored_lat, stored_long = edge_db_response_body["latitude"], edge_db_response_body["longitude"]
    obf_lat, obf_long, _ = distance(miles=25).destination((latitude, longitude), 0)
    assert (round(stored_lat, 5), round(stored_long, 5)) == (round(obf_lat, 5), round(obf_long, 5))


@exception_handler
@then(u'A JSON file is created with the HB message as its content and is stored in the edge-j1939-<env> bucket '
      u'under the file path ConvertedFiles/esn/device_id/yyyy/mm/dd/hb_file.json with no metadata')
def assert_j1939_hb_message_in_converted_files(context):
    current_dt = datetime.utcnow()
    file_key = "ConvertedFiles/{0}/{1}/{2}/{3}/{4}/".format(
        context.esn, context.device_id, current_dt.strftime("%Y"), current_dt.strftime("%m"), current_dt.strftime("%d"))
    get_key = get_key_from_list_of_s3_objects(context.final_bucket, file_key)
    assert get_key is not None
    if get_key:
        if os.path.isdir(DOWNLOAD_FOLDER_PATH):
            shutil.rmtree(DOWNLOAD_FOLDER_PATH)
        os.mkdir(DOWNLOAD_FOLDER_PATH)
        download_object_from_s3(context.final_bucket, get_key, context.download_converted_file_name)
        assert same_file_contents(context.compare_converted_file_name, context.download_converted_file_name) is True
        shutil.rmtree(DOWNLOAD_FOLDER_PATH)
        assert delete_object_from_s3(context.final_bucket, get_key) is True


@exception_handler
@then(u'A JSON file is created with the HB message as its content and is stored in the edge-j1939-<env> bucket '
      u'under the file path NGDI/esn/device_id/yyyy/mm/dd/hb_file.json with no metadata')
def assert_j1939_hb_message_in_ngdi(context):
    current_dt = datetime.utcnow()
    file_key = "NGDI/{0}/{1}/{2}/{3}/{4}/".format(
        context.esn, context.device_id, current_dt.strftime("%Y"), current_dt.strftime("%m"), current_dt.strftime("%d"))
    get_key = get_key_from_list_of_s3_objects(context.final_bucket, file_key)
    assert get_key is not None
    if get_key:
        if os.path.isdir(DOWNLOAD_FOLDER_PATH):
            shutil.rmtree(DOWNLOAD_FOLDER_PATH)
        os.mkdir(DOWNLOAD_FOLDER_PATH)
        download_object_from_s3(context.final_bucket, get_key, context.download_ngdi_file_name)
        assert same_file_contents(context.compare_ngdi_file_name, context.download_ngdi_file_name) is True
        shutil.rmtree(DOWNLOAD_FOLDER_PATH)
        assert delete_object_from_s3(context.final_bucket, get_key) is True


@exception_handler
@then(u'No JSON file is created with the HB message as its content and is stored in the edge-j1939-<env> bucket '
      u'under the file path NGDI/esn/device_id/yyyy/mm/dd/hb_file.json with no metadata')
def assert_j1939_hb_message_not_in_ngdi(context):
    file_key = "NGDI/{0}/{1}".format(context.esn, context.device_id)
    get_key = get_key_from_list_of_s3_objects(context.final_bucket, file_key)
    if get_key:
        delete_object_from_s3(context.final_bucket, get_key)
    assert get_key is None
