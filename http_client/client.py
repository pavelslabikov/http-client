import io
import socket
import ssl
import sys
import logging
import http_client.const
import http_client.errors
from yarl import URL
from http_client.utils import Request, Response

logger = logging.getLogger(__name__)


class Client:
    def __init__(
        self,
        url: str,
        method: str,
        cmd_data: str,
        upload_file: str,
        output_file: str,
        include: bool,
        user_headers: list,
        verbose: bool,
        user_agent: str,
        timeout: float,
        redirect: bool,
    ):
        self._output_mode = output_file
        self._redirect = redirect
        self._include = include
        self._timeout = timeout
        self._user_data = self.extract_input_data(upload_file, cmd_data)
        self._url = URL(url)
        if not self._url.host:
            raise http_client.errors.UrlParsingError(url)
        self._sock = self.initialize_socket(self._url.scheme, timeout)
        self.request = Request(
            method, self._url, user_headers, self._user_data, user_agent, verbose
        )

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
        """Получение ответа от сервера и переадресация на новый web-server."""
        raw_response = io.BytesIO()
        while True:
            data = self._sock.recv(http_client.const.BUFFER_SIZE)
            if not data:
                break
            raw_response.write(data)
        raw_response.seek(0)
        response = Response.from_bytes(raw_response)
        logger.info(f"Received response with code: {response.status_code}")
        if self._redirect and 301 <= response.status_code <= 307:
            logger.info(f"Redirecting to another host: {response.headers['location']}")
            self.reconnect_socket(response.headers["location"].lstrip())
            response = self.send_request()
        return response

    def reconnect_socket(self, url: str):
        """Переподключение существующего сокета к новому адресу при переадресации."""
        new_url = URL(url)
        if not new_url.host:
            raise http_client.errors.UrlParsingError(url)
        self.request.url = new_url
        self.request.headers["Host"] = new_url.host
        self._sock.close()
        self._sock = self.initialize_socket(new_url.scheme, self._timeout)

    def get_results(self, response: Response):
        """Вывод результата в файл или на stdout."""
        filename = self._output_mode
        output = sys.stdout.buffer
        if filename:
            output = open(filename, "bw")
        if self._include:
            output.write(bytes(response))
        output.write(response.message_body)
        output.close()
