import unittest
from client import Client
import argparse
import os.path


class TestClientEfficiency(unittest.TestCase):
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str)
    parser.add_argument("-a", "--agent", type=str, default="Mozilla/5.0")
    parser.add_argument("-m", "--mode", type=str, choices=["all", "body"], default="all")
    parser.add_argument("-p", "--params", type=str, default="")
    parser.add_argument("-d", "--data", type=str, default="")
    parser.add_argument("-I", "--head", action="store_true")
    parser.add_argument("-o", "--output", type=str, default="")

    def test_raises_exception_on_wrong_url(self):
        args = self.parser.parse_args(["docs.python.org/3/library/unittest.html"])
        with self.assertRaises(ValueError):
            Client(args)

    def test_url_parser(self):
        actual_address = Client.parse_link("https://docs.python.org/3/456")
        expected_address = ("docs.python.org", 443, "/3/456")
        self.assertEqual(actual_address, expected_address, f"Expected: {expected_address}, but was: {actual_address}")

    def test_file_output(self):
        args = self.parser.parse_args(['--o', '2.txt', "https://docs.python.org/3"])
        self.assertTrue(os.path.exists(os.getcwd() + "\\\\2.txt"))

    def test_head_query(self):
        args = self.parser.parse_args(['-I', "http://kremlin.ru/"])
        client = Client(args)
        response = client.send_query()
        actual_result = client.get_results("", "", response)
        self.assertTrue(actual_result.startswith("HTTP/1.1"))


if __name__ == '__main__':
    unittest.main()
