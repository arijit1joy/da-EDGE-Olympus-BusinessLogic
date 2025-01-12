import os
import json
import boto3
import datetime
import requests
import traceback
from utility import get_logger, write_to_audit_table
from edge_sqs_utility_layer import sqs_send_message
from edge_kafka_utility_layer import publish_message, create_irs_message
from edge_secretsmanager_utility_layer import get_json_value_from_secrets_manager

from edge_gps_utility_layer import handle_gps_coordinates
from edge_db_simple_layer import write_health_parameter_to_database_v2

LOGGER = get_logger(__name__)
secret_name = os.environ['PTxAPIKey']
region_name = os.environ['Region']

PT_TOPIC_INFO = os.environ["ptTopicInfo"]
MSK_SECRET_ARN = os.environ['mskSecretArn']
MSK_CLUSTER_ARN = os.environ['mskClusterArn']
KAFKA_API_VERSION_TUPLE = os.environ["KafkaApiVersionTuple"]


def handle_fc_params(converted_fc_params):
    for fc_param in converted_fc_params:
        if "activeFaultCodes" in fc_param:
            for afc in fc_param["activeFaultCodes"]:
                if "count" in afc:
                    afc["occurenceCount"] = str(afc["count"])
                    afc.pop("count")
        if "inactiveFaultCodes" in fc_param:
            fc_param.pop("inactiveFaultCodes")
        if "pendingFaultCodes" in fc_param:
            fc_param.pop("pendingFaultCodes")
    LOGGER.debug(f"Converted FC Params: {converted_fc_params}")
    return converted_fc_params


def handle_hb_params(converted_device_params, ignore_params=True):
    # De-obfuscate GPS co-ordinates
    if "Latitude" in converted_device_params and "Longitude" in converted_device_params:
        latitude = converted_device_params["Latitude"]
        longitude = converted_device_params["Longitude"]
        converted_device_params["Latitude"], converted_device_params["Longitude"] = \
            handle_gps_coordinates(latitude, longitude, deobfuscate=True)

    # Remove unnecessary params from device parameters for PT payload
    if ignore_params:
        converted_device_params = {key.lower(): value for key, value in converted_device_params.items() if
                                   key in ["Latitude", "Longitude", "Altitude"]}
    LOGGER.debug(f"Converted Device Params: {converted_device_params}")
    return converted_device_params


def store_device_health_params(converted_device_params, sample_time_stamp, device_id, esn):
    if 'messageID' in converted_device_params:
        message_id = converted_device_params['messageID']
        cpu_temperature = converted_device_params['CPU_temperature'] \
            if 'CPU_temperature' in converted_device_params else None
        pmic_temperature = converted_device_params['PMIC_temperature'] \
            if 'PMIC_temperature' in converted_device_params else None
        latitude = converted_device_params['Latitude'] if 'Latitude' in converted_device_params else None
        longitude = converted_device_params['Longitude'] if 'Longitude' in converted_device_params else None
        altitude = converted_device_params['Altitude'] if 'Altitude' in converted_device_params else None
        pdop = converted_device_params['PDOP'] if 'PDOP' in converted_device_params else None
        satellites_used = converted_device_params['Satellites_Used'] \
            if 'Satellites_Used' in converted_device_params else None
        lte_rssi = converted_device_params['LTE_RSSI'] if 'LTE_RSSI' in converted_device_params else None
        lte_rscp = converted_device_params['LTE_RSCP'] if 'LTE_RSCP' in converted_device_params else None
        lte_rsrq = converted_device_params['LTE_RSRQ'] if 'LTE_RSRQ' in converted_device_params else None
        lte_rsrp = converted_device_params['LTE_RSRP'] if 'LTE_RSRP' in converted_device_params else None
        cpu_usage_level = converted_device_params['CPU_Usage_Level'] \
            if 'CPU_Usage_Level' in converted_device_params else None
        ram_usage_level = converted_device_params['RAM_Usage_Level'] \
            if 'RAM_Usage_Level' in converted_device_params else None
        snr_per_satellite = converted_device_params['SNR_per_Satellite'] \
            if 'SNR_per_Satellite' in converted_device_params else None
        convert_timestamp = datetime.datetime.strptime(sample_time_stamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        new_timestamp = datetime.datetime.strftime(convert_timestamp, '%Y-%m-%d %H:%M:%S')
        write_health_parameter_to_database_v2(message_id, cpu_temperature, pmic_temperature, latitude, longitude,
                                           altitude, pdop, satellites_used, lte_rssi, lte_rscp, lte_rsrq, lte_rsrp,
                                           cpu_usage_level, ram_usage_level, snr_per_satellite, new_timestamp,
                                           device_id, esn)
    else:
        LOGGER.info(f"There is no messageId in Converted Device Parameter.")


def send_to_pt(post_url, headers, json_body, sqs_message_template, j1939_data_type, j1939_type, file_uuid, device_id,
               esn):
    try:
        headers_json = json.loads(headers)
        get_secret_value_response = get_json_value_from_secrets_manager(secret_name)
        if get_secret_value_response:
            api_key = get_secret_value_response['x-api-key']
            headers_json['x-api-key'] = api_key
        else:
            LOGGER.error(f"PT x-api-key not exist in secret manager")

        if "samples" in json_body:
            for sample in json_body["samples"]:
                if "convertedEquipmentFaultCodes" in sample:
                    converted_fc_params = sample["convertedEquipmentFaultCodes"]
                    fault_codes_params = handle_fc_params(converted_fc_params)
                    if fault_codes_params:
                        sample["convertedEquipmentFaultCodes"] = fault_codes_params
                    else:
                        sample.pop("convertedEquipmentFaultCodes")
                if "convertedDeviceParameters" in sample:
                    converted_device_params = sample["convertedDeviceParameters"]
                    store_device_health_params(converted_device_params, sample["dateTimestamp"],
                                               json_body["telematicsDeviceId"], json_body["componentSerialNumber"])
                    device_health_params = handle_hb_params(converted_device_params)
                    if device_health_params:
                        sample["convertedDeviceParameters"] = device_health_params
                    else:
                        sample.pop("convertedDeviceParameters")

        # We are not sending payload to PT for Digital Cockpit Device
        if json_body["telematicsDeviceId"] != '192000000000101':
            final_json_body = [json_body]
             # Send to Cluster
            if os.environ['publishKafka'].lower() == "true":
                # file_sent 

                file_sent_sqs_message = sqs_message_template \
                    .replace("{FILE_METADATA_FILE_STAGE}", "FILE_SENT")
                topicInformation = json.loads(PT_TOPIC_INFO)
                LOGGER.debug(f"topicInformation :{topicInformation}")

                topic = topicInformation["topicName"].format(j1939_type=j1939_type)
                file_type = topicInformation["file_type"]
                bu = topicInformation["bu"]
                kafka_message = create_irs_message(file_uuid, json_body, device_id, esn, topic, file_type, bu,
                                                      file_sent_sqs_message)
                LOGGER.debug(f"Data sent with IRS with kafka message :{kafka_message}, topic:{topic},fileType:{file_type},bu:{bu}")


                try:
                    publish_message(MSK_SECRET_ARN, MSK_CLUSTER_ARN, topic, kafka_message, kafka_args={'api_version': eval(KAFKA_API_VERSION_TUPLE)})
                except Exception as e:
                    error_message = f"Error while publishing the message to cluster: {e}"
                    LOGGER.error(error_message)
                    write_to_audit_table(j1939_data_type, error_message, kafka_message["telematicsDeviceId"])
            else:
                LOGGER.info("Data sent without IRS")
                # file_sent with curdatetime
                current_dt = datetime.datetime.now()
                file_sent_sqs_message = sqs_message_template \
                    .replace("{FILE_METADATA_CURRENT_DATE_TIME}",
                             current_dt.strftime('%Y-%m-%d %H:%M:%S')) \
                    .replace("{FILE_METADATA_FILE_STAGE}", "FILE_SENT")
                pt_response = requests.post(url=post_url, data=json.dumps(final_json_body), headers=headers_json)
                pt_response_body = pt_response.json()
                pt_response_code = pt_response.status_code
                LOGGER.debug(f"Post to PT response code: {pt_response_code}, body: {pt_response_body}")

                if "statusCode" in pt_response_body and pt_response_body["statusCode"] == 200:
                    sqs_send_message(os.environ["metaWriteQueueUrl"], file_sent_sqs_message)
                else:
                    LOGGER.error(f"ERROR! Posting PT : {pt_response_body}")
                    write_to_audit_table(j1939_data_type, pt_response_body, json_body["telematicsDeviceId"])

    except Exception as e:
        error_message = f"An exception occurred while posting to PT endpoint: {e}"
        LOGGER.error(error_message)
        traceback.print_exc()
        write_to_audit_table(j1939_data_type, error_message, json_body["telematicsDeviceId"])
