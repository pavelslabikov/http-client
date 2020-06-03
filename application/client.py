import io
import re
import socket
import ssl
import sys
from yarl import URL
import application.errors as errors

HEADER_EXPR = r"[a-zA-z\-]+"
STARTING_LINE_EXPR = r"(HTTP/1\.[01]) (\d\d\d)([ \w]*)"
CHUNK_SIZE = 1024


class Request:
    def __init__(self, method: str, uri: URL, headers: list, input_data, user_agent="Mozilla/5.0", verbose=False):
        self.message_body = input_data.read()
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
    def __init__(self, proto: str, code: int, phrase: str, headers: dict,
                 message_body: bytes, content_length: int, content_type: str):
        self.protocol = proto
        self.reason_phrase = phrase
        self.status_code = code
        self.headers = headers
        self.message_body = message_body
        self._raw_headers = self.get_raw_headers()
        self.content_length = content_length
        self.content_type = content_type

    @property
    def raw_headers(self):
        return self._raw_headers

    @property
    def raw_starting_line(self):
        return f"{self.protocol} {self.status_code} {self.reason_phrase}\r\n".encode()

    def get_raw_headers(self) -> bytes:
        result = bytearray()
        for name, value in self.headers.items():
            result += name.encode() + b":" + value.encode() + b"\r\n"
        result += b"\r\n"
        return result

    @classmethod
    def from_bytes(cls, raw_response: io.BytesIO):
        parsed_headers = {}
        proto, code, phrase = cls.parse_starting_line(raw_response.readline())
        line = raw_response.readline().rstrip(b"\r\n")
        while line:
            name, value = line.decode().split(":", 1)
            parsed_headers[name.lower()] = value
            line = raw_response.readline().rstrip(b"\r\n")
        content_length = int(parsed_headers.get("content-length", 0))
        content_type = parsed_headers.get("content-type", "text/plain")
        message_body = raw_response.read(content_length)
        return Response(proto, int(code), phrase.lstrip(), parsed_headers, message_body, content_length, content_type)

    @classmethod
    def parse_starting_line(cls, line: bytes):
        """Извлечение версии протокола, кода ответа и пояснения из стартовой строки ответа."""
        result = re.search(STARTING_LINE_EXPR, line.rstrip(b"\r\n").decode())
        if not result:
            raise errors.IncorrectStartingLineError(line.decode())
        return result.groups()


class Client:
    def __init__(self, url: str, method: str, cmd_data: str, upload_file: str, output_file: str, include: bool,
                 user_headers: list, verbose: bool, user_agent: str, timeout: float, redirect: bool):
        self._output_mode = output_file
        self._redirect = redirect
        self._include = include
        self._timeout = timeout
        self._user_data = self.extract_input_data(upload_file, cmd_data)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        self._url = URL(url)
        if not self._url.host:
            raise errors.UrlParsingError(url)
        self.request = Request(method, self._url, user_headers, self._user_data, user_agent, verbose)

    @staticmethod
    def extract_input_data(filename: str, cmd_data: str):
        """Извлечение входных данных из файла или с консоли."""
        if filename:
            return open(filename, "br")
        return io.BytesIO(bytes(cmd_data, "ISO-8859-1"))

    def send_request(self) -> Response:
        try:
            self._sock.connect((self.request.url.host, self.request.url.port))
            self._sock.sendall(bytes(self.request))
        except socket.gaierror:
            raise errors.ConnectingError(self.request.url.host, self.request.url.port)
        return self.receive_response()

    def receive_response(self) -> Response:
        """Получение ответа от сервера и переадресация на новый web-server."""
        raw_response = io.BytesIO()
        while True:
            data = self._sock.recv(CHUNK_SIZE)
            if not data:
                break
            raw_response.write(data)
        raw_response.seek(0)
        response = Response.from_bytes(raw_response)
        if self._redirect and 301 <= response.status_code <= 307:
            self.reconnect_socket(response.headers["location"].lstrip())
            response = self.send_request()
        return response

    def reconnect_socket(self, url: str):
        """Переподключение существующего сокета к новому адресу при переадресации."""
        new_url = URL(url)
        if not new_url.host:
            raise errors.UrlParsingError(url)
        self.request.url = new_url
        self.request.headers["Host"] = new_url.host
        self._sock.close()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self._timeout)
        if new_url.scheme == "https":
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self._sock = context.wrap_socket(self._sock)

    def get_results(self, response: Response):
        """Вывод ответа от сервера в файл или на stdout."""
        filename = self._output_mode
        output = sys.stdout.buffer
        if filename:
            output = open(filename, 'bw')
        if self._include:
            output.write(response.raw_starting_line + response.raw_headers)
        output.write(response.message_body)
        output.close()
        self.exit_client()

    def exit_client(self):
        """Завершение работы клиента."""
        self._sock.close()
        exit()


class ClientSecured(Client):
    def __init__(self, cmd_args: list):
        super().__init__(*cmd_args)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self._sock = context.wrap_socket(self._sock, server_hostname=self._url.host)
