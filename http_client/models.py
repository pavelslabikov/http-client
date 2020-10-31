import io
import re
import http_client.const
import http_client.errors
import enum
from yarl import URL


class OutputMode(enum.Enum):
    BODY = 0
    HEADERS_BODY = 1
    FULL = 2


class Request:
    def __init__(
        self,
        method: str,
        uri: URL,
        headers: list,
        input_data,
        cookies: str,
        user_agent="Mozilla/5.0",
        verbose=False,
    ):
        self.message_body = input_data.read()
        input_data.close()
        self.method = method
        self.cookies = cookies
        self.verbose = verbose
        self.url = uri
        self.user_agent = user_agent
        self.user_headers = self.parse_user_headers(headers)
        self.content_type = "text/plain"
        self.content_length = len(self.message_body)
        self.headers = self.get_request_headers()

    def get_request_headers(self) -> dict:
        headers = {
            "Host": self.url.host,
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Connection": "close",
        }
        if self.method == "POST":
            headers["Content-Length"] = self.content_length
            headers["Content-Type"] = self.content_type
        if self.cookies:
            headers["Cookie"] = self.cookies
        headers.update(self.user_headers)
        return headers

    @staticmethod
    def parse_user_headers(headers: list) -> dict:
        """Парсинг пользовательских заголовков."""
        result = {}
        for user_header in headers:
            if not re.search(http_client.const.HEADER_EXPR, user_header[0]):
                raise http_client.errors.HeaderFormatError(user_header[0])
            result[user_header[0]] = user_header[1]
        return result

    def get_results(self, mode: OutputMode) -> bytes:
        result = bytearray()
        if mode == OutputMode.FULL:
            for header, value in self.headers.items():
                result += f"-> {header}: {value}\r\n".encode()
        return result

    def __bytes__(self):
        result = bytearray(
            f"{self.method} {self.url.raw_path_qs} HTTP/1.1\r\n", "ISO-8859-1"
        )
        for header, value in self.headers.items():
            result += bytes(f"{header}: {value}\r\n", "ISO-8859-1")
        result += b"\r\n" + self.message_body + b"\r\n\r\n"
        return bytes(result)


class Response:
    def __init__(
        self,
        proto: str,
        code: int,
        phrase: str,
        headers: dict,
        message_body: bytes,
        content_length: int,
        content_type: str,
    ):
        self.proto = proto
        self.reason_phrase = phrase
        self.status_code = code
        self.headers = headers
        self.message_body = message_body
        self.content_length = content_length
        self.content_type = content_type

    @property
    def raw_headers(self):
        return "\r\n".join(
            [f"{header}:{value}" for header, value in self.headers.items()]
        ).encode()

    @property
    def raw_starting_line(self):
        return (
            f"{self.proto} {self.status_code} {self.reason_phrase}".encode()
        )

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
        return Response(
            proto,
            code,
            phrase,
            parsed_headers,
            message_body,
            content_length,
            content_type,
        )

    @classmethod
    def parse_starting_line(cls, line: bytes):
        result = re.search(
            http_client.const.STARTING_LINE, line.rstrip(b"\r\n").decode()
        )
        if not result:
            raise http_client.errors.IncorrectStartingLineError(line.decode())
        groups = result.groupdict()
        return groups["proto"], int(groups["code"]), groups["phrase"].lstrip()

    def __bytes__(self):
        return b"\r\n".join(
            [self.raw_starting_line, self.raw_headers, self.message_body]
        )

    def get_results(self, preview: OutputMode) -> bytes:
        if preview == OutputMode.BODY:
            return self.message_body
        return bytes(self)
