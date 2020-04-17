import socket
import ssl
from errors import *
from yarl import URL
import re
from arguments import ArgumentsCreator
from sys import exit

HEADER_EXPR = r"[a-zA-z]+:"


class Client:
    def __init__(self, args):
        self._user_data = self.parse_input(args.upload, args.data)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._url = URL(args.url)
        try:
            if not self._url.host:
                raise UrlParsingError("Некорректный формат введённой ссылки:", args.url)
        except UrlParsingError as error:
            print(str(error))
            self.exit_client()
        self.request = self.build_request(args)

    def build_request(self, args) -> bytes:
        """Формирование базовых, пользовательских заголовков, а так же для конкретных методов (POST)"""
        request = bytearray(f"{args.request} {self._url.raw_path_qs} HTTP/1.0\r\n", "ISO-8859-1")
        message_body = b"\r\n" + self._user_data + b"\r\n\r\n"
        headers = {"Host:": self._url.host,
                   "User-Agent:": args.agent,
                   "Accept:": "*/*",
                   "Connection:": "close"}
        if args.request == "POST":
            headers["Content-Length:"] = str(len(self._user_data))
            headers["Content-Type:"] = "text/plain"
        for user_header in args.header:
            parsed_header = self.parse_user_header(user_header)
            headers[parsed_header] = user_header[1]
        for header, value in headers.items():
            if args.verbose:
                print(f"-> {header} {value}")
            request += bytes(f"{header} {value}\r\n", "ISO-8859-1")
        request += message_body
        return request

    def parse_user_header(self, header: list) -> str:
        """Проверка корректности пользовательского запроса."""
        try:
            if not re.search(HEADER_EXPR, header[0]):
                raise HeaderFormatError("Некорректный формат пользовательского заголовка: ", header[0])
        except HeaderFormatError as error:
            print(str(error))
            self.exit_client()
        return header[0].title()

    def parse_input(self, filename: str, input_data: str) -> bytes:
        """Чтение данных из файла или с консоли."""
        if filename:
            try:
                with open(filename, "br") as file:
                    content = bytearray()
                    for line in file:
                        content += line
                return content
            except FileNotFoundError:
                print(f"Файл '{filename}' не найден.")
                exit()
        return bytes(input_data, "ISO-8859-1")

    def receive_response(self) -> bytes:
        response = bytearray()
        while True:
            data = self._sock.recv(1024)
            if not data:
                break
            response += data
        self._sock.close()
        return response

    def get_results(self, filename, mode: str, response: bytes):
        decoded_response = response.decode("cp1251", errors="ignore")
        if mode == "body":
            index = decoded_response.find("\r\n\r\n")
            decoded_response = decoded_response[index + 4:]
        if filename:
            try:
                with open(filename, 'w') as file:
                    file.write(decoded_response)
            except OSError as e:
                print(f'{type(e)}: {e}')
                self.exit_client()
        return decoded_response

    def send_request(self):
        try:
            self._sock.connect((self._url.host, self._url.port))
            self._sock.sendall(self.request)
        except socket.gaierror:
            print(f"Не удалось подключиться по заданному адресу: {self._url.host}, {self._url.port}")
            self.exit_client()
        except Exception as e:
            print(f'{type(e)}: {e}')
            self.exit_client()
        return self.receive_response()

    def exit_client(self):
        self._sock.close()
        exit()


class ClientSecured(Client):
    def __init__(self, args):
        super().__init__(args)
        self._sock = ssl.wrap_socket(self._sock)

    def send_request(self):
        self._sock.connect((self._url.host, self._url.port))
        self._sock.do_handshake()
        self._sock.sendall(self.request)
        return self.receive_response()


def main():
    parser = ArgumentsCreator().set_up_arguments()
    cmd_args = parser.parse_args()
    if cmd_args.url.startswith('https'):
        client = ClientSecured(cmd_args)
    else:
        client = Client(cmd_args)
    server_response = client.send_request()
    result = client.get_results(cmd_args.output, cmd_args.mode, server_response)
    if not cmd_args.output:
        print(result)


if __name__ == '__main__':
    main()
