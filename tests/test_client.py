import unittest
from application.client import Client, ClientSecured
import application.errors as errors
import warnings


class TestClientEfficiency(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.default_args = {
            "Agent": "",
            "URL": "",
            "Method": "",
            "Data": "",
            "Output": "",
            "Include": False,
            "Headers": [],
            "Verbose": False,
            "Upload": "",
            "Debug": True
        }
        warnings.simplefilter("ignore", ResourceWarning)

    def test_output_modes(self):
        cases = [{"Method": "HEAD", "URL": "http://ptsv2.com/"},
                 {"Method": "OPTIONS", "URL": "http://ptsv2.com/"},
                 {"Method": "POST", "Data": "test", "Include": True, "URL": "http://ptsv2.com/"},
                 {"Include": True, "URL": "http://ptsv2.com/"}]
        other_cases = [{"Output": "test_file.txt", "Method": "POST", "Data": "test", "URL": "http://ptsv2.com/"},
                       {"Output": "test_file.txt", "URL": "http://ptsv2.com/"},
                       {"Output": "test_file.txt", "Data": "test", "URL": "http://ptsv2.com/"}]
        for test_case in cases:
            actual = self.get_actual_response(test_case)
            self.assertTrue(actual.startswith(b"HTTP/1.1 200 OK"))
        self.setUp()

        for test_case in other_cases:
            self.prepare_args(test_case)
            self.default_args["Debug"] = False
            client = Client(self.default_args)
            server_response = client.send_request()
            try:
                client.get_results(server_response)
            except SystemExit:
                pass
            with open("test_file.txt", "rb") as file:
                actual = file.read(64)
            self.assertTrue(actual.startswith(b"<!DOCTYPE html>"))

    def test_https_domains(self):
        cases = [{"Method": "HEAD", "URL": "https://stackoverflow.com/"},
                 {"Method": "HEAD", "URL": "https://ulearn.me/"},
                 {"Method": "OPTIONS", "URL": "https://www.microsoft.com/ru-ru/"}]
        for test_case in cases:
            self.prepare_args(test_case)
            client = ClientSecured(self.default_args)
            server_response = client.send_request()
            actual = client.get_results(server_response).read(64)
            self.assertTrue(actual.startswith(b"HTTP/1.1 200 OK"))

    def test_http_methods(self):
        cases = [{"Method": "HEAD", "URL": "http://ptsv2.com/"},
                 {"Method": "OPTIONS", "URL": "http://ptsv2.com/"},
                 {"Method": "POST", "Data": "test", "URL": "http://ptsv2.com/"}]
        for test_case in cases:
            actual = self.get_actual_response(test_case)
            self.assertTrue(actual.startswith(b"HTTP/1.1 200 OK"))

    def test_adding_wrong_headers(self):
        cases = [{"Headers": [["123", "text"]], "URL": "http://ptsv2.com/"},
                 {"Headers": [["!#$%", "text"]], "URL": "http://ptsv2.com/"},
                 {"Headers": [["Correct", "header"], ["!#$%", "text"]], "URL": "http://ptsv2.com/"},
                 {"Headers": [["123", "456"], ["!#$%", "text"]], "URL": "http://ptsv2.com/"}]
        for test_case in cases:
            self.prepare_args(test_case)
            try:
                Client(self.default_args)
            except SystemExit:
                pass
            except errors.HeaderFormatError:
                assert True
            else:
                assert False

    def test_changing_user_agent(self):
        cases = [{"Headers": [["User-Agent", "sample"]], "URL": "http://ptsv2.com/"},
                 {"Headers": [["User-Agent", "sample"]], "URL": "http://ptsv2.com/"},
                 {"Agent": "sample", "URL": "http://ptsv2.com/"}]
        for test_case in cases:
            self.prepare_args(test_case)
            client = Client(self.default_args)
            self.assertTrue(client.req_headers["User-Agent"] == "sample")

    def test_wrong_format_url(self):
        cases = [{"URL": "12345"},
                 {"URL": "!@#$%^&"}]
        for test_case in cases:
            self.prepare_args(test_case)
            try:
                Client(self.default_args)
            except SystemExit:
                pass
            except errors.UrlParsingError:
                assert True
            else:
                assert False

    def test_changing_adding_headers(self):
        cases = [{"Headers": [["Connection", "keep-alive"]], "URL": "http://ptsv2.com/"},
                 {"Headers": [["New-Header", "123"]], "URL": "http://ptsv2.com/"},
                 {"Headers": [["New-Header", "123"], ["Connection", "keep-alive"]], "URL": "http://ptsv2.com/"}]
        for test_case in cases:
            self.prepare_args(test_case)
            client = Client(self.default_args)
            for header in test_case["Headers"]:
                self.assertEqual(client.req_headers[header[0]], header[1])

    def get_actual_response(self, test_case) -> bytes:
        self.prepare_args(test_case)
        client = Client(self.default_args)
        server_response = client.send_request()
        return client.get_results(server_response).read(128)

    def prepare_args(self, test_case):
        for header, value in test_case.items():
            self.default_args[header] = value


if __name__ == '__main__':
    unittest.main()
