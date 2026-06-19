#
# Copyright (c) 2025 Composiv.ai
#
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
#
# Contributors:
#   Composiv.ai - initial API and implementation
#

import json
import unittest
from unittest.mock import MagicMock, patch

import rclpy

from muto_core.auth_adapters import NoneAuthAdapter, OAuth2Adapter
from muto_core.twin import Twin


class TestTwin(unittest.TestCase):

    def setUp(self):
        self.node = Twin()
        self.node.twin_url = "http://sandbox.composiv.ai"
        self.node.anonymous = "true"
        self.node.namespace = "org.eclipse.muto.sandbox"
        self.node.name = "composer-test"
        self.node.type = "test_car"
        self.node.unique_name = ""
        self.node.attributes = '{"brand": "muto", "model": "test_model"}'
        self.node.definition = ""
        self.node.topic = "test_topic"
        self.node.thing_id = "test_thing_id"
        # Use a no-op auth strategy by default so tests unrelated to
        # authentication aren't coupled to the OAuth2 token flow.
        self.node.auth_adapter = NoneAuthAdapter()
        self.node.get_logger = MagicMock()

    @classmethod
    def setUpClass(cls):
        rclpy.init()

    @classmethod
    def tearDownClass(cls):
        rclpy.shutdown()

    @patch.object(Twin, "stack")
    def test_get_current_properties(self, mock_stack):
        self.node.get_current_properties()
        mock_stack.assert_called_once_with("test_thing_id")

    @patch.object(Twin, "stack")
    def test_get_stack_definition(self, mock_stack):
        test_stack_id = "test_stack_id"
        self.node.get_stack_definition(test_stack_id)
        mock_stack.assert_called_once_with("test_stack_id")

    @patch("requests.request")
    def test_stack(self, mock_req):
        returned_value = self.node.stack(self.node.thing_id)

        self.assertIsNone(returned_value)
        mock_req.assert_called_once_with(
            "get",
            "http://sandbox.composiv.ai/api/2/things/test_thing_id/features/stack",
            headers={},
        )

    @patch("requests.request")
    def test_stack_status_error(self, mock_req):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_req.return_value = mock_response
        returned_value = self.node.stack(self.node.thing_id)

        self.assertEqual(returned_value, {})
        mock_req.assert_called_once_with(
            "get",
            "http://sandbox.composiv.ai/api/2/things/test_thing_id/features/stack",
            headers={},
        )

    @patch("requests.request")
    def test_stack_status_ok(self, mock_req):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"properties":"test_properties","properties_second":"test_properties_second" }'
        mock_req.return_value = mock_response
        returned_value = self.node.stack(self.node.thing_id)

        self.assertEqual(returned_value, "test_properties")
        mock_req.assert_called_once_with(
            "get",
            "http://sandbox.composiv.ai/api/2/things/test_thing_id/features/stack",
            headers={},
        )

    @patch("requests.request")
    def test_stack_auth_failure_skips_request(self, mock_req):
        self.node.auth_adapter = MagicMock()
        self.node.auth_adapter.apply.return_value = None

        returned_value = self.node.stack(self.node.thing_id)

        self.assertIsNone(returned_value)
        mock_req.assert_not_called()

    @patch("requests.request")
    def test_set_current_stack(self, mock_req):
        test_stack = MagicMock()
        test_stack.status_code = 200
        test_stack.text = "test_output"
        mock_req.return_value = test_stack
        self.node.set_current_stack("test_stack_id","test_state")
        self.node.get_logger().info.assert_called_once_with("Status Code: 200, Response: test_output")
        mock_req.assert_called_once_with(
            "put",
            "http://sandbox.composiv.ai/api/2/things/test_thing_id/features/stack/properties/current",
            headers={"Content-type": "application/json"},
            json={"stackId":"test_stack_id", "state":"test_state"},
        )

    def test_set_current_stack_none(self):
        returned_value = self.node.set_current_stack(None)
        self.assertIsNone(returned_value)

    def test_get_context(self):
        returned_value = self.node.get_context()
        self.assertEqual(
            returned_value,
            {
                "namespace": "org.eclipse.muto.sandbox",
                "topic": "test_topic",
                "twin_url": "http://sandbox.composiv.ai",
                "type": "test_car",
                "unique_name": "",
                "thing_id": "test_thing_id",
                "anonymous": "true",
            },
        )

    @patch.object(Twin, "device_register_data")
    @patch("requests.request")
    def test_register_device_status_400(self, mock_req, mock_device_register_data):
        mock_response_patch = MagicMock()
        mock_response_put = MagicMock()

        mock_response_patch.status_code = 400
        mock_response_put.status_code = 201

        mock_req.side_effect = [mock_response_patch, mock_response_put]

        self.node.register_device()

        self.assertEqual(mock_req.call_count, 2)
        self.assertEqual(mock_req.call_args_list[0].args[0], "patch")
        self.assertEqual(mock_req.call_args_list[1].args[0], "put")
        self.assertTrue(self.node.is_device_registered)
        self.node.get_logger().info.assert_called_once_with(
            "Device registered successfully."
        )
        mock_device_register_data.assert_called()

    @patch.object(Twin, "device_register_data")
    @patch("requests.request")
    def test_register_device_status_404(self, mock_req, mock_device_register_data):
        mock_response_patch = MagicMock()
        mock_response_put = MagicMock()

        mock_response_patch.status_code = 404
        mock_response_put.status_code = 201

        mock_req.side_effect = [mock_response_patch, mock_response_put]

        self.node.register_device()
        self.assertEqual(mock_req.call_count, 2)
        self.assertEqual(mock_req.call_args_list[0].args[0], "patch")
        self.assertEqual(mock_req.call_args_list[1].args[0], "put")
        self.assertTrue(self.node.is_device_registered)
        self.node.get_logger().info.assert_called_once_with(
            "Device registered successfully."
        )
        mock_device_register_data.assert_called()

    @patch.object(Twin, "device_register_data")
    @patch("requests.request")
    def test_register_device_status_201(self, mock_req, mock_device_register_data):
        mock_response_patch = MagicMock()

        mock_response_patch.status_code = 201

        mock_req.return_value = mock_response_patch
        self.node.register_device()
        mock_req.assert_called_once()
        self.assertEqual(mock_req.call_args_list[0].args[0], "patch")
        self.assertTrue(self.node.is_device_registered)
        self.node.get_logger().info.assert_called_once_with(
            "Device registered successfully."
        )
        mock_device_register_data.assert_called()

    @patch.object(Twin, "device_register_data")
    @patch("requests.request")
    def test_register_device_status_204(self, mock_req, mock_device_register_data):
        mock_response_patch = MagicMock()

        mock_response_patch.status_code = 204

        mock_req.return_value = mock_response_patch
        self.node.register_device()
        mock_req.assert_called_once()
        self.assertEqual(mock_req.call_args_list[0].args[0], "patch")
        self.assertTrue(self.node.is_device_registered)
        self.node.get_logger().info.assert_called_once_with(
            "Device registered successfully."
        )
        mock_device_register_data.assert_called()

    @patch.object(Twin, "device_register_data")
    @patch("requests.request")
    def test_register_device_status_unknown(self, mock_req, mock_device_register_data):
        mock_response_patch = MagicMock()

        mock_response_patch.status_code = 300

        mock_req.return_value = mock_response_patch
        self.node.register_device()
        mock_req.assert_called_once()
        self.assertEqual(mock_req.call_args_list[0].args[0], "patch")
        self.assertFalse(self.node.is_device_registered)
        self.node.get_logger().info.assert_not_called()
        self.node.get_logger().warn.assert_called_once_with(
            "Device registration was unsuccessful. Status Code: 300."
        )

        mock_device_register_data.assert_called()

    def test_register_device_auth_failure_returns_404(self):
        self.node.auth_adapter = MagicMock()
        self.node.auth_adapter.apply.return_value = None

        with patch("requests.request") as mock_req:
            status_code = self.node.register_device()

        mock_req.assert_not_called()
        self.assertEqual(status_code, 404)
        self.assertFalse(self.node.is_device_registered)

    @patch("requests.post")
    def test_register_device_uses_oauth2_bearer_token(self, mock_post):
        self.node.auth_adapter = OAuth2Adapter(
            self.node, "https://jwt.example/token", "client-id", "client-secret"
        )
        mock_post.return_value.json.return_value = {"access_token": "abc123"}

        with patch("requests.request") as mock_req:
            mock_req.return_value.status_code = 201
            self.node.register_device()

        self.assertEqual(
            mock_req.call_args_list[0].kwargs["headers"]["Authorization"],
            "Bearer abc123",
        )

    def test_get_credentials_delegates_to_adapter(self):
        self.node.auth_adapter = MagicMock()
        self.node.auth_adapter.get_credentials.return_value = {"access_token": "abc123"}

        result = self.node.get_credentials()

        self.assertEqual(result, {"access_token": "abc123"})
        self.node.auth_adapter.get_credentials.assert_called_once()

    @patch("requests.request")
    def test_get_registered_telemetries(self, mock_req):
        mock_response_patch = MagicMock()

        mock_response_patch.status_code = 200
        mock_response_patch.text = (
            '{"properties":"test_properties","payload":"test_payload"}'
        )
        mock_req.return_value = mock_response_patch

        self.node.get_registered_telemetries()

        self.node.get_logger().info.assert_called_once_with(
            "Telemetry properties received successfully."
        )

    @patch("requests.request")
    def test_get_registered_telemetries_status_404(self, mock_req):
        mock_response_patch = MagicMock()

        mock_response_patch.status_code = 404
        mock_response_patch.text = (
            '{"properties":"test_properties","payload":"test_payload"}'
        )

        mock_req.return_value = mock_response_patch
        returned_value = self.node.get_registered_telemetries()

        self.assertEqual(
            returned_value, {"properties": "test_properties", "payload": "test_payload"}
        )
        self.node.get_logger().warn.assert_called_once_with(
            'Getting telemetry properties was unsuccessful - 404 {"properties":"test_properties","payload":"test_payload"}.'
        )

    @patch("requests.request")
    @patch.object(Twin, "get_registered_telemetries")
    def test_register_telemetry_201(self, mock_get_registered_telemetries, mock_req):
        test_telemetry = json.dumps({"definition": "test"})
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_req.return_value = mock_response
        self.node.register_telemetry(test_telemetry)
        mock_get_registered_telemetries.assert_called_once()
        mock_req.assert_called_once_with(
            "put",
            "http://sandbox.composiv.ai/api/2/things/test_thing_id/features/telemetry/properties/definition",
            headers={"Content-type": "application/json"},
            json=[{"definition": "test"}],
        )
        self.node.get_logger().info.assert_called_once_with(
            "Telemetry registered successfully."
        )

    @patch("requests.request")
    @patch.object(Twin, "get_registered_telemetries")
    def test_register_telemetry_204(self, mock_get_registered_telemetries, mock_req):
        test_telemetry = json.dumps({"definition": "test"})
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_req.return_value = mock_response
        self.node.register_telemetry(test_telemetry)
        mock_get_registered_telemetries.assert_called_once()
        mock_req.assert_called_once_with(
            "put",
            "http://sandbox.composiv.ai/api/2/things/test_thing_id/features/telemetry/properties/definition",
            headers={"Content-type": "application/json"},
            json=[{"definition": "test"}],
        )
        self.node.get_logger().info.assert_called_once_with(
            "Telemetry modified successfully."
        )

    @patch("requests.request")
    @patch.object(Twin, "get_registered_telemetries")
    def test_register_telemetry_404(self, mock_get_registered_telemetries, mock_req):
        test_telemetry = json.dumps({"definition": "test"})
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_req.return_value = mock_response
        self.node.register_telemetry(test_telemetry)
        mock_get_registered_telemetries.assert_called_once()
        mock_req.assert_called_once_with(
            "put",
            "http://sandbox.composiv.ai/api/2/things/test_thing_id/features/telemetry/properties/definition",
            headers={"Content-type": "application/json"},
            json=[{"definition": "test"}],
        )
        self.node.get_logger().warn.assert_called_once_with(
            "Telemetry registration was unsuccessful - 404."
        )

    @patch("requests.request")
    @patch.object(Twin, "get_registered_telemetries")
    def test_delete_telemetry_204(self, mock_get_registered_telemetries, mock_req):
        test_telemetry = json.dumps({"definition": "test_delete"})
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_req.return_value = mock_response
        self.node.delete_telemetry(test_telemetry)
        mock_get_registered_telemetries.assert_called_once()
        mock_req.assert_called_once_with(
            "put",
            "http://sandbox.composiv.ai/api/2/things/test_thing_id/features/telemetry/properties/definition",
            headers={"Content-type": "application/json"},
            json=[],
        )
        self.node.get_logger().info.assert_called_once_with(
            "Telemetry deleted successfully."
        )

    @patch("requests.request")
    @patch.object(Twin, "get_registered_telemetries")
    def test_delete_telemetry_404(self, mock_get_registered_telemetries, mock_req):
        test_telemetry = json.dumps({"definition": "test_delete"})
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_req.return_value = mock_response
        self.node.delete_telemetry(test_telemetry)
        mock_get_registered_telemetries.assert_called_once()
        mock_req.assert_called_once_with(
            "put",
            "http://sandbox.composiv.ai/api/2/things/test_thing_id/features/telemetry/properties/definition",
            headers={"Content-type": "application/json"},
            json=[],
        )
        self.node.get_logger().warn.assert_called_once_with(
            "Telemetry deletion was unsuccessful - 404."
        )

    def test_default_auth_adapter_is_none(self):
        node = Twin()
        self.assertIsInstance(node.auth_adapter, NoneAuthAdapter)

    def test_device_register_data(self):
        returned_value = self.node.device_register_data()
        self.assertEqual(
            returned_value,
            {
                "definition": "",
                "attributes": '{"brand": "muto", "model": "test_model"}',
                "features": {
                    "context": {"properties": {}},
                    "stack": {"properties": {}},
                    "telemetry": {"properties": {}},
                },
            },
        )

    @patch("socket.socket")
    def test_connection_failure(self, mock_socket):
        mock_socket.node = MagicMock()
        mock_socket.return_value = mock_socket.node

        self.node.twin_url = "device@server"

        mock_socket.node.connect.side_effect = OSError("Connection failed")

        with patch.object(self.node, "get_logger") as mock_logger:
            self.node.connection_status()
            mock_logger().warn.assert_called_once_with(
                "Twin Server ping failed: Connection failed"
            )

        self.assertFalse(self.node.internet_status)

    @patch("socket.socket")
    def test_device_registration(self, mock_socket):
        mock_socket.node = MagicMock()
        mock_socket.return_value = mock_socket.node

        self.node.twin_url = "device@server"

        self.node.is_device_registered = False
        with patch.object(self.node, "register_device") as mock_register_device:
            self.node.connection_status()
            mock_register_device.assert_called_once()

        self.node.is_device_registered = True
        with patch.object(self.node, "register_device") as mock_register_device:
            self.node.connection_status()
            mock_register_device.assert_not_called()


if __name__ == "__main__":
    unittest.main()
