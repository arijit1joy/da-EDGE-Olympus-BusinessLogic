import sys
import json
import unittest
from unittest.mock import ANY, patch, MagicMock

sys.path.append("../")

from tests.cda_module_mock_context import CDAModuleMockingContext

with  CDAModuleMockingContext(sys) as cda_module_mock_context, patch.dict("os.environ", {
    "ptTopicInfo":'{"topicName": "nimbuspt_j1939-{j1939_type}", "bu":"PSBU","file_type":"JSON"}',
    "LoggingLevel": "debug",
    "PTxAPIKey": "testKey",
    "Region": "us-east-1",
    "region": "us-east-1",
    'EDGEDBReader_ARN': 'arn:::12345',
    "edgeCommonAPIURL": "testurl",
    "publishKafka": "true",
    "CDPTJ1939PostURL": "testurl",
    "CDPTJ1939Header": "testheader",
    "RedisSecretName": "testsecret",
    "EndpointFile": "EndpointFile",
    "CPPostBucket": "CPPostBucket",
    "EndpointBucket": "EndpointBucket",
    "JSONFormat": "JSONFormat",
    "PSBUSpecifier": "psbu",
    "EBUSpecifier": "ebu",
    "UseEndpointBucket": "UseEndpointBucket",
    "PTJ1939PostURL": "PTJ1939PostURL",
    "PTJ1939Header": "PTJ1939Header",
    "PowerGenValue": "PowerGenValue",
    "mapTspFromOwner": "true",
    "ProcessDataQuality": "true",
    "DataQualityLambda": "DataQualityLambda",
    "MaxAttempts": "2",
    "EngineStatOverride":"EngineStat_9",
    "LoadFactorOverride":"LoadFactor_9",
    "EngineStatSc":"SC8091",
    "LoadFactorSc":"SC8093",
    "pcc_role_arn": "arn",
    "j1939_stream_arn": "arn",
    "pcc_region": "us-east-1"

}):
    cda_module_mock_context.mock_module("boto3")

    cda_module_mock_context.mock_module("post")
    cda_module_mock_context.mock_module("pt_poster")
    cda_module_mock_context.mock_module("pcc_poster")
    cda_module_mock_context.mock_module("utility")
    cda_module_mock_context.mock_module("edge_db_lambda_client"),
    cda_module_mock_context.mock_module("edge_sqs_utility_layer.sqs_utility")
    cda_module_mock_context.mock_module("update_scheduler")
    cda_module_mock_context.mock_module("EdgeDbLambdaClient")

    import PosterLambda


class TestPosterLambda(unittest.TestCase):
    sample_device_id = '12345'

    
    @patch.dict("os.environ", {"QueueUrl": "test-url"})
    @patch("PosterLambda.boto3.client")
    def test_delete_message_from_sqs_queue_successful(self, mock_client):
        """
        Test for delete_message_from_sqs_queue() running successfully.
        """
        mock_client.return_value.delete_message.return_value = "test-response"

        response = PosterLambda.delete_message_from_sqs_queue("test-handle")

        mock_client.return_value.delete_message.assert_called_with(QueueUrl="test-url", ReceiptHandle="test-handle")
        self.assertEqual(response, "test-response")


    @patch("PosterLambda.EDGE_DB_CLIENT")
    def test_getDeviceInfo_success(self, mock_db_reader):
        mock_db_reader.execute.return_value = [{'test': 'value'}]
        result = PosterLambda.get_device_info(self.sample_device_id)
        self.assertEqual(result, {'test': 'value'})
        mock_db_reader.execute.assert_called_once()


    @patch("PosterLambda.EDGE_DB_CLIENT")
    def test_getDeviceInfo_uncaughtException(self, mock_db_reader):
        mock_db_reader.execute.side_effect = Exception("Mock db reader exception")
        result = PosterLambda.get_device_info(self.sample_device_id)
        self.assertEqual(result, False)
        mock_db_reader.execute.assert_called_once()


    @patch("PosterLambda.EDGE_DB_CLIENT")
    def test_getDeviceInfo_caughtException(self, mock_db_reader):
        mock_db_reader.execute.return_value = None
        result = PosterLambda.get_device_info(self.sample_device_id)
        self.assertEqual(result, False)
        self.assertEqual(mock_db_reader.execute.call_count, 2)


    def test_get_business_partner_ebu(self):
        """
        Test for get_business_partner() returning `EBU` when EBUSpecifier is supplied.
        """
        response = PosterLambda.get_business_partner("EBU")
        self.assertEqual(response, "EBU")


    def test_get_business_partner_psbu(self):
        """
        Test for get_business_partner() returning `PSBU` when PSBUSpecifier is supplied.
        """
        response = PosterLambda.get_business_partner("PSBU")
        self.assertEqual(response, "PSBU")


    def test_get_business_partner_other(self):
        """
        Test for get_business_partner() returning False when other device types are supplied.
        """
        response = PosterLambda.get_business_partner("other")
        self.assertEqual(response, False)


    @patch("PosterLambda.EDGE_DB_CLIENT")
    def test_retrieve_and_process_file(self, mock_db_reader):
        mock_db_reader.execute.return_value = None
        #record="{'Records': [{'eventVersion': '2.1', 'eventSource': 'aws:s3', 'awsRegion': 'us-east-1', 'eventTime': '2023-06-20T13:39:14.168Z', 'eventName': 'ObjectCreated:Put', 'userIdentity': {'principalId': 'AWS:AROA2VJPF5G4LHXPR7XXA:da-edge-j1939-ObfuscateGPSCoordinates-dev'}, 'requestParameters': {'sourceIPAddress': '3.227.253.155'}, 'responseElements': {'x-amz-request-id': 'DZ0JTJRECFJJM1JF', 'x-amz-id-2': 'cwXhQMeFC2CakRlyIHlos2yO4w66mchIgq9TTalxwkelR0P1EtM1ra8feH2UuDs7AasL5FBWPYM1yQDjZ6RZWAcZxlt1RyZC+ejRIhpELhw='}, 's3': {'s3SchemaVersion': '1.0', 'configurationId': '3930cedb-6716-4db5-af13-d93125ae976b', 'bucket': {'name': 'edge-j1939-dev', 'ownerIdentity': {'principalId': 'A2LE772XLDSELB'}, 'arn': 'arn:aws:s3:::edge-j1939-dev'}, 'object': {'key': 'ConvertedFiles/19299951/192999999999953/2023/06/20/EDGE_192999999999953_19299951_BDD002_1687268354.json', 'size': 1768, 'eTag': '63f216bb2036a645b07df7ffe1e07974', 'sequencer': '006491AC02212B7B66'}}}]}"
        s3_event_body = '{"Records":"abc"}'
        receipt_handle = "AQEBvlwydQHQJU4agXcgek9j3OTsyXYIym6xFUk/Kkq3Djt1vbEu4yoA43cNSPM6euyILXuZaaqjp2kApLPBYER6bnK9IFRb53ZhkGUDOONkVINRxMgGdywOHl8xvoAo1OeNpoL0efs08aO+diR+RVrKo1mGrNC6DGMv5GrtVFtquJ4+GPs9T28ioKUpAOvSlwbvLaEg7L+w4y16AGRf56axVOK84I/EdYdtZhLhAqqZDxz/GvAMWF2+B3GAEmtpJ7iPu/ddDarQbESH3MyvpfS0R6aIRo6oSmZsroxX8sfjznG6/RFbw2eLtU9+ffOan+yXKd4Nn3PUfx9m6aXjjP4o9zB4qlfa9/MXsAnGrMCvKq52ejsUrdtO4JKAtowArn0J4l+99K8WufYnS0LxoDuE5goaFoK5UNUopzsK5lDIMDM="#record["receiptHandle"]
        #result = PosterLambda.retrieve_and_process_file(s3_event_body,receipt_handle)

        #self.assertEqual(result, False)
        #self.assertEqual(mock_db_reader.execute.call_count, 2)

if __name__ == '__main__':
    unittest.main()
