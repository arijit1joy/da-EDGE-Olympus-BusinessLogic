import sys
import unittest
from unittest.mock import patch
import time

from tests.cda_module_mock_context import CDAModuleMockingContext

with CDAModuleMockingContext(sys) as cda_module_mock_context, patch.dict('os.environ', {
    'AWS_LAMBDA_FUNCTION_NAME': 'lambda'
}):
    cda_module_mock_context.mock_module("utility")
    cda_module_mock_context.mock_module("utilities.redis_utility")
    cda_module_mock_context.mock_module("edge_db_lambda_client")
    import update_scheduler


class TestUpdateScheduler(unittest.TestCase):
    """
    Test module for update_scheduler.py
    """

    REDIS_EXPIRY = 5 * 24 * 60 * 60


    def test_get_request_id_from_consumption_view_query_successful(self):
        """
        Test for _get_request_id_from_consumption_view_query() running successfully.
        """
        response = update_scheduler._get_request_id_from_consumption_view_query(
            "J1939_HB",
            "EDGE_357649070803120_64100016_SC5079", {'device_owner': 'PSBU', 'pcc_claim_status': 'CLAIMED', 'cust_ref': 'cust-ref', 'equip_id': 'equip-id', 'vin': 'vin'}
        )

        expected_response = "SELECT da_edge_olympus.scheduler.request_id " + \
            "FROM da_edge_olympus.data_requester_information " + \
            "JOIN da_edge_olympus.scheduler " + \
            "ON da_edge_olympus.data_requester_information.request_id=da_edge_olympus.scheduler.request_id " + \
            "WHERE da_edge_olympus.data_requester_information.data_type='J1939_CD_HB' " + \
            "AND da_edge_olympus.scheduler.device_id='357649070803120' " + \
            "AND da_edge_olympus.scheduler.engine_serial_number='64100016' " + \
            "AND SUBSTRING(da_edge_olympus.scheduler.config_spec_file_name,1,6)='SC5079' " + \
            "AND da_edge_olympus.scheduler.status IN ('Config Accepted','Data Rx In Progress','Config Sent')"
        
        self.assertEqual(response, expected_response)

    def test_get_request_id_from_consumption_view_query_successful_ebu(self):
        """
        Test for _get_request_id_from_consumption_view_query() running successfully.
        """
        response = update_scheduler._get_request_id_from_consumption_view_query(
            "J1939_HB",
            "EDGE_357649070803120_64100016_SC5079", {'device_owner': 'EBU', 'pcc_claim_status': 'CLAIMED', 'cust_ref': 'cust-ref', 'equip_id': 'equip-id', 'vin': 'vin'}
        )

        expected_response = "SELECT da_edge_olympus.scheduler.request_id " + \
                            "FROM da_edge_olympus.data_requester_information " + \
                            "JOIN da_edge_olympus.scheduler " + \
                            "ON da_edge_olympus.data_requester_information.request_id=da_edge_olympus.scheduler.request_id " + \
                            "WHERE da_edge_olympus.data_requester_information.data_type='J1939_CD_HB' " + \
                            "AND da_edge_olympus.scheduler.device_id='357649070803120' " + \
                            "AND da_edge_olympus.scheduler.engine_serial_number='64100016' " + \
                            "AND SUBSTRING(da_edge_olympus.scheduler.config_spec_file_name,1,6)='SC5079' " + \
                            "AND da_edge_olympus.scheduler.status IN ('Config Accepted','Data Rx In Progress','Config Sent','Config Rejected','Config Association Failed')"

        self.assertEqual(response, expected_response)


    def test_get_request_id_from_consumption_view_query_successful_device_owner_none(self):
        """
        Test for _get_request_id_from_consumption_view_query() running successfully.
        """
        response = update_scheduler._get_request_id_from_consumption_view_query(
            "J1939_HB",
            "EDGE_357649070803120_64100016_SC5079", {'device_owner': 'None', 'pcc_claim_status': 'CLAIMED', 'cust_ref': 'cust-ref', 'equip_id': 'equip-id', 'vin': 'vin'}
        )

        expected_response = "SELECT da_edge_olympus.scheduler.request_id " + \
                            "FROM da_edge_olympus.data_requester_information " + \
                            "JOIN da_edge_olympus.scheduler " + \
                            "ON da_edge_olympus.data_requester_information.request_id=da_edge_olympus.scheduler.request_id " + \
                            "WHERE da_edge_olympus.data_requester_information.data_type='J1939_CD_HB' " + \
                            "AND da_edge_olympus.scheduler.device_id='357649070803120' " + \
                            "AND da_edge_olympus.scheduler.engine_serial_number='64100016' " + \
                            "AND SUBSTRING(da_edge_olympus.scheduler.config_spec_file_name,1,6)='SC5079' " + \
                            "AND da_edge_olympus.scheduler.status IN ('Config Accepted','Data Rx In Progress','Config Sent')"

        self.assertEqual(response, expected_response)


    @patch("update_scheduler._get_request_id_from_consumption_view_query")
    @patch("update_scheduler.get_set_redis_value")
    def test_get_request_id_from_consumption_view_successful(self, mock_get_set_redis_value, mock_query_fn):
        """
        Test for get_request_id_from_consumption_view() running successfully.
        """
        mock_query_fn.return_value = "query"
        mock_get_set_redis_value.return_value = [{"request_id": "req-id"}]
        device_info = {'device_owner': 'PSBU', 'pcc_claim_status': 'CLAIMED', 'cust_ref': 'cust-ref', 'equip_id': 'equip-id',
                       'vin': 'vin'}

        response = update_scheduler.get_request_id_from_consumption_view(
            "J1939_HB",
            "EDGE_357649070803120_64100016_SC5079", device_info
        )

        mock_get_set_redis_value.assert_called_with(
            "req_id@@j1939_hb@@edge_357649070803120_64100016_sc5079",
            "query",
            self.REDIS_EXPIRY
        )
        self.assertEqual(response, "req-id")

    @patch("update_scheduler._get_request_id_from_consumption_view_query")
    @patch("update_scheduler.get_set_redis_value")
    def test_get_request_id_from_consumption_view_on_error(self, mock_get_set_redis_value, mock_query_fn):
        """
        Test for get_request_id_from_consumption_view() when it throws an exception.
        """
        mock_query_fn.return_value = "query"
        mock_get_set_redis_value.side_effect = Exception

        with self.assertRaises(Exception):
            update_scheduler.get_request_id_from_consumption_view(
                "J1939_HB",
                "EDGE_357649070803120_64100016_SC5079"
            )

    @patch("update_scheduler.get_update_scheduler_query")
    @patch("update_scheduler.EDGE_DB_CLIENT")
    def test_update_scheduler_table_successful(self, mock_db_client, mock_scheduler):
        """
        Test for update_scheduler_table() running successfully.
        """
        mock_scheduler.return_value = "query"

        update_scheduler.update_scheduler_table("REQ1233", "102900000000003", {'device_owner': 'PSBU', 'pcc_claim_status': 'CLAIMED', 'cust_ref': 'cust-ref', 'equip_id': 'equip-id', 'vin': 'vin'})

        mock_db_client.execute.assert_called_with("query", method="WRITE")

    @patch("update_scheduler.get_update_scheduler_query")
    @patch("update_scheduler.EDGE_DB_CLIENT")
    def test_update_scheduler_table_on_error(self, mock_db_client, mock_scheduler):
        """
        Test for update_scheduler_table() when it throws an exception.
        """
        mock_scheduler.return_value = "query"
        mock_db_client.execute.side_effect = Exception

        with self.assertRaises(Exception):
            update_scheduler.update_scheduler_table("REQ1233", "102900000000003")

    def test_get_update_scheduler_query_given_request_id_deviceid_then_return_query(self):
        time_format = '%Y-%m-%d %H:%M:%S'
        time_default_format = time.localtime()
        current_date_time = time.strftime(time_format, time_default_format)
        response = update_scheduler.get_update_scheduler_query(
            "REQ12345",
            "357649070803120",
            {'device_owner': 'PSBU', 'pcc_claim_status': 'CLAIMED', 'cust_ref': 'cust-ref', 'equip_id': 'equip-id', 'vin': 'vin'}
        )

        expected_response = "UPDATE da_edge_olympus.scheduler " + \
                            "SET status='Data Rx In Progress',updated_date_time='"+current_date_time+"',updated_by='lambda' " + \
                            "WHERE request_id='REQ12345' " + \
                            "AND device_id='357649070803120' " + \
                            "AND status IN ('Config Accepted','Config Sent')"
        self.assertEqual(response, expected_response)


    def test_get_update_scheduler_query_given_request_id_deviceid_ebu_device_owner_then_return_query(self):
        time_format = '%Y-%m-%d %H:%M:%S'
        time_default_format = time.localtime()
        current_date_time = time.strftime(time_format, time_default_format)
        response = update_scheduler.get_update_scheduler_query(
            "REQ12345",
            "357649070803120",
            {'device_owner': 'EBU', 'pcc_claim_status': 'CLAIMED', 'cust_ref': 'cust-ref', 'equip_id': 'equip-id', 'vin': 'vin'}
        )

        expected_response = "UPDATE da_edge_olympus.scheduler " + \
                            "SET status='Data Rx In Progress',updated_date_time='"+current_date_time+"',updated_by='lambda' " + \
                            "WHERE request_id='REQ12345' " + \
                            "AND device_id='357649070803120' " + \
                            "AND status IN ('Config Accepted','Config Sent','Config Rejected','Config Association Failed')"
        self.assertEqual(response, expected_response)


    def test_get_update_scheduler_query_given_request_id_deviceid_null_device_owner_then_return_query(self):
        time_format = '%Y-%m-%d %H:%M:%S'
        time_default_format = time.localtime()
        current_date_time = time.strftime(time_format, time_default_format)
        response = update_scheduler.get_update_scheduler_query(
            "REQ12345",
            "357649070803120",
            {'device_owner': None, 'pcc_claim_status': 'CLAIMED', 'cust_ref': 'cust-ref', 'equip_id': 'equip-id', 'vin': 'vin'}
        )

        expected_response = "UPDATE da_edge_olympus.scheduler " + \
                            "SET status='Data Rx In Progress',updated_date_time='"+current_date_time+"',updated_by='lambda' " + \
                            "WHERE request_id='REQ12345' " + \
                            "AND device_id='357649070803120' " + \
                            "AND status IN ('Config Accepted','Config Sent')"
        self.assertEqual(response, expected_response)