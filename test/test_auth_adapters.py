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

import base64
import unittest
from unittest.mock import MagicMock, patch

from muto_core.auth_adapters import (
    BasicAuthAdapter,
    NoneAuthAdapter,
    OAuth2Adapter,
    create_auth_adapter,
)


class TestNoneAuthAdapter(unittest.TestCase):

    def test_apply_leaves_headers_unchanged(self):
        adapter = NoneAuthAdapter()
        result = adapter.apply({"Content-type": "application/json"})
        self.assertEqual(result, {"Content-type": "application/json"})


class TestBasicAuthAdapter(unittest.TestCase):

    def test_apply_adds_basic_auth_header(self):
        adapter = BasicAuthAdapter("ditto", "ditto")
        result = adapter.apply({"Content-type": "application/json"})

        expected_credentials = base64.b64encode(b"ditto:ditto").decode()
        self.assertEqual(result["Content-type"], "application/json")
        self.assertEqual(result["Authorization"], f"Basic {expected_credentials}")

    def test_apply_does_not_mutate_input_headers(self):
        adapter = BasicAuthAdapter("ditto", "ditto")
        headers = {}
        adapter.apply(headers)
        self.assertEqual(headers, {})


class TestOAuth2Adapter(unittest.TestCase):

    def setUp(self):
        self.node = MagicMock()
        self.adapter = OAuth2Adapter(
            self.node, "https://jwt.example/token", "client-id", "client-secret"
        )

    @patch("requests.post")
    def test_get_jwt_token(self, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "abc123"}

        token = self.adapter.get_jwt_token()

        self.assertEqual(token, {"access_token": "abc123"})
        mock_post.assert_called_once_with(
            "https://jwt.example/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": "client-id",
                "client_secret": "client-secret",
            },
        )

    @patch("requests.post")
    def test_apply_attaches_bearer_token(self, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "abc123"}

        result = self.adapter.apply({"Content-type": "application/json"})

        self.assertEqual(result["Authorization"], "Bearer abc123")
        self.assertEqual(result["Content-type"], "application/json")

    @patch("requests.post")
    def test_apply_returns_none_when_token_missing(self, mock_post):
        mock_post.return_value.json.return_value = {}

        result = self.adapter.apply({})

        self.assertIsNone(result)
        self.node.get_logger().error.assert_called_once_with(
            "Error occurred while getting JWT token..."
        )


class TestCreateAuthAdapter(unittest.TestCase):

    def setUp(self):
        self.node = MagicMock()

    def test_creates_none_adapter(self):
        adapter = create_auth_adapter("none", self.node)
        self.assertIsInstance(adapter, NoneAuthAdapter)

    def test_creates_basic_adapter(self):
        adapter = create_auth_adapter("basic", self.node, username="u", password="p")
        self.assertIsInstance(adapter, BasicAuthAdapter)
        self.assertEqual(adapter.username, "u")
        self.assertEqual(adapter.password, "p")

    def test_creates_oauth2_adapter(self):
        adapter = create_auth_adapter(
            "oauth2",
            self.node,
            jwt_url="https://jwt.example/token",
            jwt_client_id="client-id",
            jwt_client_secret="client-secret",
        )
        self.assertIsInstance(adapter, OAuth2Adapter)
        self.assertEqual(adapter.jwt_url, "https://jwt.example/token")

    def test_unknown_auth_type_defaults_to_oauth2(self):
        adapter = create_auth_adapter("client_cert", self.node)
        self.assertIsInstance(adapter, OAuth2Adapter)

    def test_empty_auth_type_defaults_to_oauth2(self):
        adapter = create_auth_adapter("", self.node)
        self.assertIsInstance(adapter, OAuth2Adapter)

    def test_auth_type_is_case_insensitive(self):
        adapter = create_auth_adapter("Basic", self.node, username="u", password="p")
        self.assertIsInstance(adapter, BasicAuthAdapter)


if __name__ == "__main__":
    unittest.main()
