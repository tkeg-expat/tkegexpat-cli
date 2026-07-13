# tests/test_auth_forwarding.py
import os
import unittest
from tkegexpat import api


class BuildRequestAuth(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("TKEGEXPAT_FORWARD_COOKIE", None)

    def test_forwards_cookie_when_env_present(self):
        os.environ["TKEGEXPAT_FORWARD_COOKIE"] = "u1=abc; s1=def"
        req = api._build_request("/api/1.1/obj/product")
        self.assertEqual(req.get_header("Cookie"), "u1=abc; s1=def")
        self.assertIsNone(req.get_header("Authorization"))

    def test_no_cookie_header_when_env_absent(self):
        req = api._build_request("/api/1.1/obj/product", token="tok|uid")
        self.assertIsNone(req.get_header("Cookie"))
        self.assertEqual(req.get_header("Authorization"), "Bearer tok|uid")

    def test_empty_env_sends_no_cookie_header(self):
        os.environ["TKEGEXPAT_FORWARD_COOKIE"] = ""
        req = api._build_request("/api/1.1/obj/product")
        self.assertIsNone(req.get_header("Cookie"))
