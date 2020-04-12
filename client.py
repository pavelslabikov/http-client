import socket
import re
import argparse
import ssl

URL_EXPR = r'https?://([\w\.]+)\.([a-z]{2,6}\.?)(/[\w\.]*)*/?'


class Client:
    def __init__(self, args):
        self._user_agent = args.agent
        self._address = self.parse_link(args.url)
        self._user_data = args.data
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self._address[1] == 443:
            self._sock = ssl.wrap_socket(sock)
        else:
            self._sock = sock
        if args.data != '':
            self.target_method = self.post
        elif args.head:
            self.target_method = self.head
        else:
            self.target_method = self.get
            self._user_data = args.params

    @staticmethod
    def parse_link(link: str) -> tuple:
        port = 80
        if link.startswith('https'):
            port = 443
        pattern = re.compile(URL_EXPR)
        parsed_url = pattern.search(link)
        if parsed_url is None:
            raise ValueError("Incorrect format of URL")
        host = f'{parsed_url[1]}.{parsed_url[2]}'
        uri = link[parsed_url.end(2):]
        return host, port, uri

    def get(self, params: str):
        query = f"GET {self._address[2] + params} HTTP/1.0\r\n" \
                f"Host: {self._address[0]}\r\n" \
                f"User-Agent: {self._user_agent}\r\n" \
                "Accept: */*\r\n" \
                "Connection: close\r\n\r\n"
        self._sock.send(bytes(query, "ISO-8859-1"))
        return self.receive_response()

    def post(self, body: str):
        query = f"POST {self._address[2]} HTTP/1.0\r\n" \
                f"Host: {self._address[0]}\r\n" \
                "Accept: */*\r\n" \
                "Content-Type: application/x-urlencoded\r\n" \
                f"User-Agent: {self._user_agent}\r\n" \
                f"Content-Length: {len(body)}\r\n" \
                f"Connection: close\r\n\r\n{body}\r\n\r\n"
        self._sock.send(bytes(query, "ISO-8859-1"))
        return self.receive_response()

    def head(self, data=""):
        query = f"HEAD {self._address[2]} HTTP/1.0\r\n" \
                f"Host: {self._address[0]}\r\n" \
                f"User-Agent: {self._user_agent}\r\n" \
                "Accept: */*\r\n" \
                "Connection: close\r\n\r\n"
        self._sock.send(bytes(query, "ISO-8859-1"))
        return self.receive_response()

    def receive_response(self) -> bytearray:
        response = bytearray()
        while True:
            data = self._sock.recv(1024)
            if not data:
                break
            response.extend(data)
        self._sock.close()
        return response

    def get_results(self, filename, mode: str, response: bytearray):
        decoded_response = response.decode("utf_8", errors='ignore')
        if mode == "body":
            index = decoded_response.find("\r\n\r\n")
            decoded_response = decoded_response[index + 4:]
        if filename != '':
            with open(filename, 'w') as file:
                file.write(decoded_response)
        return decoded_response

    def send_query(self):
        self._sock.connect((self._address[0], self._address[1]))
        if type(self._sock) is ssl.SSLSocket:
            self._sock.do_handshake()
        return self.target_method(self._user_data)


def main():
    parser = argparse.ArgumentParser()
    methods = parser.add_mutually_exclusive_group()
    parser.add_argument("url", type=str, help="Ссылка на ресурс в формате:")
    parser.add_argument("-a", "--agent", type=str, help="Указать свой USER_AGENT", default="Mozilla/5.0")
    parser.add_argument("-m", "--mode", type=str, choices=["all", "body"],
                        help="Режим вывода ответа от сервера", default="all")
    parser.add_argument("-o", "--output", type=str, help="Записывает вывод в файл вместо stdout.", default="")
    methods.add_argument("-p", "--params", type=str, help="Указать GET-параметры", default="")
    methods.add_argument("-d", "--data", type=str, help="Отправить данные методом POST", default="")
    methods.add_argument("-I", "--head", action="store_true", help="Отправить запрос при помощи метода HEAD")

    cmd_args = parser.parse_args()
    client = Client(cmd_args)
    server_response = client.send_query()
    result = client.get_results(cmd_args.output, cmd_args.mode, server_response)
    if cmd_args.output == '':
        print(result)


if __name__ == '__main__':
    main()
