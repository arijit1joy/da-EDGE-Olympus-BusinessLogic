import os
from edge_logger import logging_framework, send_error_to_audit_trail_queue


def logger_and_file_name(file_name):
    converted_file_name = ''.join([word.capitalize() for word in file_name.split('_')])
    logger = logging_framework(f"ObfuscateGPSCoordinates.{converted_file_name}", os.environ["LoggingLevel"])

    return logger


def write_to_audit_table(error_message):
    error_params = {"module_name": "J1939_HB", "error_code": "500", "error_message": error_message,
                    "component_name": "ObfuscateGPS", "device_id": "No Device ID"}
    send_error_to_audit_trail_queue(os.environ["AuditTrailQueueUrl"], error_params)
