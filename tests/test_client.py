import unittest
from client import Client, ClientSecured
import socket
from arguments import ArgumentsCreator
from errors import *


class TestClientEfficiency(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.parser = ArgumentsCreator().set_up_arguments()

    def test_https_domains(self):
        cases = [["-X", "HEAD", "https://www.python.org/"],
                 ["https://ulearn.me/"]]
        for test_case in cases:
            curr_args = self.parser.parse_args(test_case)
            client = ClientSecured(curr_args)
            server_response = client.send_request()
            result = client.get_results("", "", server_response)
            self.assertTrue(result.startswith("HTTP/1.1 200 OK"))

    def test_http_domains(self):
        cases = [["-X", "HEAD", "http://www.ng.ru/"],
                 ["http://kremlin.ru/"]]
        for test_case in cases:
            curr_args = self.parser.parse_args(test_case)
            client = Client(curr_args)
            server_response = client.send_request()
            result = client.get_results("", "", server_response)
            self.assertTrue(result.startswith("HTTP/1.1 200 OK"))

    def test_adding_wrong_headers(self):
        cases = [["-H", "123:", "content", "http://ptsv2.com/"],
                 ["-H", "?#$!@:", "content", "http://ptsv2.com/"]]
        for test_case in cases:
            current_args = self.parser.parse_args(test_case)
            try:
                Client(current_args)
            except HeaderFormatError:
                assert True
            except SystemExit:
                pass
            else:
                assert False

    def test_changing_user_agent(self):
        cases = [["-a", "Chrome", "http://ptsv2.com/"],
                 ["-H", "User-Agent:", "Chrome", "http://ptsv2.com/"]]
        for test_case in cases:
            curr_args = self.parser.parse_args(test_case)
            client = Client(curr_args)
            self.assertTrue(b"User-Agent: Chrome" in client.request)
            server_response = client.send_request()
            client.get_results("", "", server_response)

    def test_wrong_format_url(self):
        cases = [["12345abcdef"],
                 ["-X", "HEAD", "pslabikov@mail.ru"],
                 [""], ["google.com"]]
        for test_case in cases:
            curr_args = self.parser.parse_args(test_case)
            try:
                Client(curr_args)
            except HeaderFormatError:
                assert True
            except SystemExit:
                pass
            else:
                assert False

    def test_changing_adding_headers(self):
        cases = [["-X", "POST", "-H", "Content-Type:", "text/plain", "http://ptsv2.com/"],
                 ["-X", "HEAD", "-H", "Cookie:", "a=3", "http://ptsv2.com/"]]
        for test_case in cases:
            curr_args = self.parser.parse_args(test_case)
            client = Client(curr_args)
            self.assertTrue(bytes(f"{test_case[3]} {test_case[4]}", "ISO-8859-1") in client.request)
            server_response = client.send_request()
            client.get_results("", "", server_response)


if __name__ == '__main__':
    unittest.main()
