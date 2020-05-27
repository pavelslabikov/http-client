import io
import re
import socket
import ssl
import sys
from yarl import URL
import application.errors as errors

HEADER_EXPR = r"[a-zA-z\-]+"


class Client:
    def __init__(self, cmd_args: dict):
        self.req_headers = {}
        self._args = cmd_args
        self._user_data = self.extract_input_data()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._url = URL(cmd_args["URL"])
        if not self._url.host:
            raise errors.UrlParsingError(cmd_args["URL"])
        self.request = self.build_request()

    def build_request(self) -> bytes:
        """Формирование базовых, пользовательских заголовков, а так же для конкретных методов (POST)"""
        target_method = self._args['Method']
        if self._args["Data"] or self._args["Upload"]:
            target_method = "POST"
        request = bytearray(f"{target_method} {self._url.raw_path_qs} HTTP/1.1\r\n", "ISO-8859-1")
        message_body = b"\r\n" + self._user_data.read() + b"\r\n\r\n"
        self._user_data.seek(0)
        self.req_headers = {"Host": self._url.host,
                            "User-Agent": self._args['Agent'],
                            "Accept": "*/*",
                            "Connection": "close"}
        if target_method == "POST":
            self.req_headers["Content-Length"] = str(len(self._user_data.read()))
            self.req_headers["Content-Type"] = "text/plain"
        for user_header in self._args['Headers']:
            parsed_header = Client.parse_user_header(user_header)
            self.req_headers[parsed_header] = user_header[1]
        for header, value in self.req_headers.items():
            if self._args['Verbose']:
                print(f"-> {header}: {value}")
            request += bytes(f"{header}: {value}\r\n", "ISO-8859-1")
        request += message_body
        self._user_data.close()
        return request

    @staticmethod
    def parse_user_header(header: list) -> str:
        """Проверка корректности пользовательских заголовков."""
        if not re.search(HEADER_EXPR, header[0]):
            raise errors.HeaderFormatError(header[0])
        return header[0]

    def extract_input_data(self):
        """Извлечение входных данных из файла или с консоли."""
        filename = self._args["Upload"]
        if filename:
            return open(filename, "br")

        return io.BytesIO(bytes(self._args["Data"], "ISO-8859-1"))

    def receive_response(self):
        response = io.BytesIO()
        while True:
            data = self._sock.recv(1024)
            if not data:
                break
            response.write(data)
        self._sock.close()
        return response

    def get_results(self, response: io.BytesIO) -> io.BytesIO:
        filename = self._args["Output"]
        response.seek(0)
        if self._args["Debug"]:
            return response
        part = response.read(1024)
        if not self._args["Include"] and self._args["Method"] != "HEAD" and self._args["Method"] != "OPTIONS":
            index = part.find(b"\r\n\r\n")
            while index == -1:
                part = response.read(1024)
                index = part.find(b"\r\n\r\n")
            part = part[index + 4:]
        if filename:
            with open(filename, 'bw') as file:
                while part:
                    file.write(part)
                    part = response.read(1024)
            response.close()
            self.exit_client()
        while part:
            sys.stdout.buffer.write(part)
            sys.stderr.flush()
            part = response.read(1024)

    def send_request(self):
        try:
            self._sock.connect((self._url.host, self._url.port))
            self._sock.sendall(self.request)
        except socket.gaierror:
            raise errors.ConnectingError(self._url.host, self._url.port)
        return self.receive_response()

    def exit_client(self):
        self._sock.close()
        exit()


class ClientSecured(Client):
    def __init__(self, cmd_args):
        super().__init__(cmd_args)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self._sock = context.wrap_socket(self._sock, server_hostname=self._url.host)
