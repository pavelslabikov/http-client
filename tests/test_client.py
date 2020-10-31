import unittest
import unittest.mock as mock
from http_client.client import Client
from http_client.models import Request, Response
import http_client.errors as errors
import warnings
import io
from yarl import URL


class TestResponseMethods(unittest.TestCase):
    def test_incorrect_starting_lines(self):
        cases = ["HTTP/1. 101 OK", "HTTPS/1.1 101 OK",
                 "123", "HTTP/1.1 10 OK"]
        for test_case in cases:
            with self.subTest(case=test_case), self.assertRaises(
                errors.IncorrectStartingLineError
            ):
                response_message = io.BytesIO(test_case.encode() + b"\r\n")
                Response.from_bytes(response_message)

    def test_parsing_headers(self):
        starting_line = b"HTTP/1.1 101 OK\r\n"
        cases = [
            "Server: test\r\nCookie: 1",
            "no-spaces:test",
            "Empty-Header:",
            "Spaces : test",
            "",
        ]
        for test_case in cases:
            with self.subTest(case=test_case):
                response_message = io.BytesIO(
                    starting_line + test_case.encode() + b"\r\n\r\n"
                )
                actual = Response.from_bytes(response_message).headers
                expected = {}
                for header in test_case.split("\r\n"):
                    if header == "":
                        continue
                    name, value = header.split(":")
                    expected[name.lower()] = value
                self.assertDictEqual(actual, expected)

    def test_getting_status(self):
        cases = ["HTTP/1.1 100 OK", "HTTP/1.0 404", "HTTP/1.1 500 oooK"]
        for test_case in cases:
            with self.subTest(case=test_case):
                response = io.BytesIO(test_case.encode() + b"\r\n\r\n")
                actual_code = Response.from_bytes(response).status_code
                expected_code = int(test_case.split(" ")[1])
                self.assertEqual(actual_code, expected_code)

    def test_parsing_message_body(self):
        starting_line = b"HTTP/1.1 101 OK\r\n"
        cases = [
            b"Content-Length: 3\r\n\r\n123",
            b"Empty: body\r\n\r\n",
            b"Content-Length: 3\r\nsecond:header\r\n\r\n123",
        ]
        for test_case in cases:
            with self.subTest(case=test_case):
                response_message = io.BytesIO(starting_line + test_case)
                actual_body = Response.from_bytes(
                    response_message
                ).message_body
                expected_body = test_case[test_case.find(b"\r\n\r\n") + 4:]
                self.assertEqual(actual_body, expected_body)


class TestRequestMethods(unittest.TestCase):
    def test_adding_wrong_headers(self):
        cases = [
            [["123", "text"]],
            [["!#$%", "text"]],
            [["Correct", "header"], ["!#$%", "text"]],
            [["123", "456"], ["!#$%", "text"]],
        ]
        for test_case in cases:
            with self.subTest(case=test_case), self.assertRaises(
                errors.HeaderFormatError
            ):
                Request.parse_user_headers(test_case)

    def test_adding_changing_headers(self):
        cases = [
            [["Connection", "keep-alive"]],
            [["New-Header", "123"]],
            [["New-Header", "123"], ["Connection", "keep-alive"]],
        ]
        for test_case in cases:
            with self.subTest(case=test_case):
                actual_headers = Request(
                    "GET", URL("vk.com/"), test_case, io.BytesIO(), ""
                ).user_headers
                expected_headers = {}
                for header in test_case:
                    name, value = header
                    expected_headers[name] = value
                self.assertDictEqual(actual_headers, expected_headers)

    def test_request_starting_line(self):
        cases = [
            ["GET", URL("http://vk.com/"), [], io.BytesIO(), ""],
            ["POST", URL("http://vk.com/path"), [], io.BytesIO(), ""],
        ]
        for case in cases:
            with self.subTest(case=case):
                actual = bytes(Request(*case))
                method, path = case[0], case[1].raw_path_qs
                expected = f"{method} {path} HTTP/1.1\r\n".encode()
                self.assertTrue(actual.startswith(expected))


class TestClientEfficiency(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.default_args = {
            "url": "https://example.com/",
            "method": "GET",
            "data": "",
            "upload": "",
            "include": False,
            "headers": [],
            "verbose": False,
            "agent": "",
            "timeout": None,
            "redirect": False,
            "cookies": None,
        }
        warnings.simplefilter("ignore", ResourceWarning)

    def test_upload_modes(self):
        with mock.patch(
            "http_client.client.Client.extract_input_data",
            return_value=io.BytesIO(b"test"),
        ), self.subTest("Return value - BytesIO"):
            actual_user_data = Client(
                *self.default_args.values()
            ).request.message_body
            self.assertEqual(actual_user_data, b"test")

        with open("test_file.txt", "bw") as test_file:
            test_file.write(b"test")

        with mock.patch(
            "http_client.client.Client.extract_input_data",
            return_value=open("test_file.txt", "br"),
        ), self.subTest("Return value - FileIO"):
            actual_user_data = Client(
                *self.default_args.values()
            ).request.message_body
            self.assertEqual(actual_user_data, b"test")

    def test_http_methods(self):
        cases = [
            {"method": "HEAD"},
            {"method": "OPTIONS"},
            {"method": "POST", "data": "test"},
            {"method": "GET"},
        ]
        for test_case in cases:
            with self.subTest(test_case):
                self.default_args.update(test_case)
                actual_method = Client(
                    *self.default_args.values()
                ).request.method
                self.assertEqual(actual_method, test_case["method"])

    def test_wrong_format_url(self):
        cases = [
            {"url": "12345"},
            {"url": "!@#$%^&"},
            {"url": ""},
            {"url": "www.vk.com/im"},
            {"url": "https://"},
        ]
        for test_case in cases:
            self.default_args.update(test_case)
            with self.assertRaises(errors.UrlParsingError):
                Client(*self.default_args.values())

    def test_changing_user_agent(self):
        cases = [
            {"agent": "test"},
            {"headers": [["User-Agent", "test"]]},
            {
                "headers": [
                    ["user-agent", "test"],
                    ["connection", "keep-alive"],
                ]
            },
        ]
        for test_case in cases:
            with self.subTest(case=test_case):
                self.default_args.update(test_case)
                actual_agent = Client(
                    *self.default_args.values()
                ).request.user_agent
                self.assertEqual(actual_agent, "test")


class TestClientNetworkInteraction(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.default_args = {
            "url": "",
            "method": "GET",
            "data": "",
            "upload": "",
            "include": False,
            "headers": [],
            "verbose": False,
            "agent": "",
            "timeout": None,
            "redirect": False,
            "cookies": None,
        }
        warnings.simplefilter("ignore", ResourceWarning)

    def test_https_domains(self):
        cases = [
            {"url": "https://m.vk.com/"},
            {"method": "HEAD", "url": "https://stackoverflow.com/"},
            {"method": "POST", "url": "https://ulearn.me/"},
            {"method": "OPTIONS", "url": "https://www.microsoft.com/ru-ru/"},
        ]
        for test_case in cases:
            with self.subTest(test_case["url"]):
                self.default_args.update(test_case)
                client = Client(*self.default_args.values())
                response = client.send_request()
                actual_status, actual_phrase = (
                    response.status_code,
                    response.reason_phrase,
                )
                self.assertEqual(actual_status, 200)
                self.assertEqual(actual_phrase, "OK")

    def test_http_domains(self):
        cases = [
            {"url": "http://htmlbook.ru/"},
            {"url": "http://gov.ru/"},
            {"url": "http://tadviser.ru/", "redirect": True},
        ]
        for test_case in cases:
            with self.subTest(test_case["url"]):
                self.default_args.update(test_case)
                client = Client(*self.default_args.values())
                response = client.send_request()
                actual_status, actual_phrase = (
                    response.status_code,
                    response.reason_phrase,
                )
                self.assertEqual(actual_status, 200)
                self.assertEqual(actual_phrase, "OK")

    def test_redirection(self):
        cases = [
            {"url": "https://vk.com/", "redirect": True},
            {"url": "https://google.com/", "redirect": True},
        ]
        for test_case in cases:
            with self.subTest(test_case["url"]):
                self.default_args.update(test_case)
                client = Client(*self.default_args.values())
                response = client.send_request()
                actual_status, actual_phrase = (
                    response.status_code,
                    response.reason_phrase,
                )
                self.assertEqual(actual_status, 200)
                self.assertEqual(actual_phrase, "OK")


if __name__ == "__main__":
    unittest.main()
