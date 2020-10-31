import io
import socket
import ssl
import logging
import http_client.const
import http_client.errors
from yarl import URL
from http_client.models import Request, Response

logger = logging.getLogger(__name__)


class Client:
    def __init__(
        self,
        url: str,
        method: str,
        cmd_data: str,
        upload_file: str,
        include: bool,
        user_headers: list,
        verbose: bool,
        user_agent: str,
        timeout: float,
        redirect: bool,
        cookie_file: str,
    ):
        self._redirect = redirect
        self._include = include
        self._timeout = timeout
        self._user_data = self.extract_input_data(upload_file, cmd_data)
        self._cookies = self.extract_cookies(cookie_file)
        self._url = URL(url)
        if not self._url.host:
            raise http_client.errors.UrlParsingError(url)
        self._sock = self.initialize_socket(self._url.scheme, timeout)
        self.request = Request(
            method,
            self._url,
            user_headers,
            self._user_data,
            self._cookies,
            user_agent,
            verbose,
        )

    @staticmethod
    def extract_cookies(filename: str) -> str:
        if not filename:
            return ""

        with open(filename, "r") as file:
            result = []
            for cookie in file.readlines():
                if cookie.rstrip("\n"):
                    result.append(cookie.rstrip("\n"))

            return URL(";".join(result)).raw_path

    @staticmethod
    def initialize_socket(scheme: str, timeout: float) -> socket.socket:
        result_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result_socket.settimeout(timeout)
        if scheme == "https":
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context.wrap_socket(result_socket)
        return result_socket

    @staticmethod
    def extract_input_data(filename: str, cmd_data: str):
        """Извлечение входных данных из файла или с консоли."""
        if filename:
            logger.info(f"Trying to open file: {filename}")
            return open(filename, "br")
        return io.BytesIO(cmd_data.encode("ISO-8859-1"))

    def send_request(self) -> Response:
        try:
            logger.info(f"Attempting to connect to: {self.request.url.host}")
            self._sock.connect((self.request.url.host, self.request.url.port))
            self._sock.sendall(bytes(self.request))
        except socket.gaierror:
            raise http_client.errors.ConnectingError(
                self.request.url.host, self.request.url.port
            )
        return self.receive_response()

    def receive_response(self) -> Response:
        raw_response = io.BytesIO()
        while True:
            data = self._sock.recv(http_client.const.BUFFER_SIZE)
            if not data:
                break
            raw_response.write(data)
        raw_response.seek(0)
        response = Response.from_bytes(raw_response)
        logger.info(f"Received response with code: {response.status_code}")
        if self._redirect and 301 <= response.status_code < 400:
            logger.info(
                f"Redirecting to host: {response.headers['location']}"
            )
            self.reconnect_socket(response.headers["location"].lstrip())
            response = self.send_request()
        return response

    def reconnect_socket(self, url: str):
        new_url = URL(url)
        if not new_url.host:
            raise http_client.errors.UrlParsingError(url)
        self.request.url = new_url
        self.request.headers["Host"] = new_url.host
        self._sock.close()
        self._sock = self.initialize_socket(new_url.scheme, self._timeout)
