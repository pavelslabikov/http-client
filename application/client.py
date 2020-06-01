import io
import re
import socket
import ssl
import sys
from yarl import URL
import application.errors as errors

HEADER_EXPR = r"[a-zA-z\-]+"
STARTING_LINE_EXPR = r"HTTP/1\.[01] (\d\d\d) \w+"


class Request:
    def __init__(self, method: str, uri: URL, headers: list, input_data, user_agent: str, verbose: bool):
        self.message_body = input_data.read()  # TODO: Исправить полное чтение потока
        input_data.close()
        self.method = method
        self.verbose = verbose
        self.url = uri
        self.user_agent = user_agent
        self.user_headers = self.parse_user_headers(headers)
        self.content_type = "text/plain"
        self.content_length = len(self.message_body)
        self.headers = self.get_request_headers()

    def get_request_headers(self) -> dict:
        """Формирование базовых, пользовательских заголовков, а так же для конкретных методов (POST)"""
        headers = {"Host": self.url.host,
                   'User-Agent': self.user_agent,
                   "Accept": "*/*",
                   "Connection": "close"}
        if self.method == "POST":
            headers["Content-Length"] = self.content_length
            headers["Content-Type"] = self.content_type
        headers.update(self.user_headers)
        return headers

    @staticmethod
    def parse_user_headers(headers: list) -> dict:
        """Парсинг пользовательских заголовков."""
        result = {}
        for user_header in headers:
            if not re.search(HEADER_EXPR, user_header[0]):
                raise errors.HeaderFormatError(user_header[0])
            result[user_header[0]] = user_header[1]
        return result

    def __bytes__(self):
        result = bytearray(f"{self.method} {self.url.raw_path_qs} HTTP/1.1\r\n", "ISO-8859-1")
        for header, value in self.headers.items():
            if self.verbose:
                print(f"-> {header}: {value}")
            result += bytes(f"{header}: {value}\r\n", "ISO-8859-1")
        result += b"\r\n" + self.message_body + b"\r\n\r\n"
        return bytes(result)


class Response:
    def __init__(self, status_code: int, headers: dict, message_body: io.BytesIO, raw_headers: bytes):
        self.status_code = status_code
        self.headers = headers
        self.message_body = message_body
        self.headers_as_bytes = raw_headers

    @classmethod
    def from_bytes(cls, raw_response: io.BytesIO):
        raw_response.seek(0)
        part = raw_response.read(1024)  # TODO: Фиксануть чтение по 1024 байт
        raw_headers = bytearray()
        message_body = io.BytesIO()
        index = part.find(b"\r\n\r\n")
        while index == -1:
            raw_headers += part
            part = raw_response.read(1024)
        raw_headers += part[:index]
        message_body.write(part[index + 4:])
        part = raw_response.read(1024)
        while part:
            message_body.write(part)
            part = raw_response.read(1024)
        message_body.seek(0)
        http_status_code = cls.get_status(raw_headers)
        parsed_headers = cls.parse_headers(raw_headers)
        return Response(http_status_code, parsed_headers, message_body, raw_headers)

    @classmethod
    def parse_headers(cls, raw_headers: bytes) -> dict:
        """Парсинг заголовков из байтов в словарь"""
        result = {}
        headers_list = raw_headers.split(b"\r\n")
        for header in headers_list[1:]:
            new_header = str(header).split(":")
            result[new_header[0]] = new_header[1]
        return result

    @classmethod
    def get_status(cls, raw_headers: bytes) -> int:
        """Извлечение кода ответа от сервера из стартовой строки"""
        index = raw_headers.find(b"\r\n")
        result = re.search(STARTING_LINE_EXPR, str(raw_headers[:index]))
        if not result:
            pass  # TODO: throw exception
        return int(result.group(1))


class Client:
    def __init__(self, args: dict):
        self._output_mode = args["Output"]
        self._debug_mode = args["Debug"]
        self._include = args["Include"]
        self._user_data = self.extract_input_data(args["Upload"], args["Data"])
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._url = URL(args["URL"])
        if not self._url.host:
            raise errors.UrlParsingError(args["URL"])
        self.request = Request(args["Method"], self._url, args["Headers"], self._user_data,
                               args["Agent"], args["Verbose"])

    @staticmethod
    def extract_input_data(filename: str, cmd_data: str):
        """Извлечение входных данных из файла или с консоли."""
        if filename:
            return open(filename, "br")
        return io.BytesIO(bytes(cmd_data, "ISO-8859-1"))

    def send_request(self):
        try:
            self._sock.connect((self._url.host, self._url.port))
            self._sock.sendall(bytes(self.request))
        except socket.gaierror:
            raise errors.ConnectingError(self._url.host, self._url.port)
        return self.receive_response()

    def receive_response(self) -> Response:
        response = io.BytesIO()
        while True:
            data = self._sock.recv(1024)
            if not data:
                break
            response.write(data)
        self._sock.close()
        return Response.from_bytes(response)

    def get_results(self, response: Response) -> Response:
        filename = self._output_mode
        if self._debug_mode:
            return response
        output = sys.stdout.buffer
        if filename:
            output = open(filename, 'bw')
        if self._include:
            output.write(response.headers_as_bytes)
        part = response.message_body.read(1024)
        while part:
            output.write(part)
            part = response.message_body.read(1024)
        output.close()
        self.exit_client()

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
