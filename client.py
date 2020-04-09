import socket
import re
import argparse

URL_EXPR = r'https?://([\w\.]+)\.([a-z]{2,6}\.?)(/[\w\.]*)*/?'


class Client:
    def __init__(self, args):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._user_agent = args.agent
        address = self.parse_link(args.url)
        self._sock.connect((address[0], address[1]))
        if args.data != '':
            response = self.post(address, args.data)
        elif args.head:
            response = self.head(address)
        else:
            response = self.get(address, args.params)
        self._sock.close()
        self.parse_response(args.mode, response)

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

    def get(self, uri, params: str):
        query = f"GET {uri[2] + params} HTTP/1.0\r\n" \
                f"Host: {uri[0]}\r\n" \
                f"User-Agent: {self._user_agent}\r\n" \
                "Accept: */*\r\n" \
                "Connection: close\r\n\r\n"
        self._sock.send(bytes(query, "ISO-8859-1"))
        return self.get_response()

    def post(self, uri, body: str):
        query = f"POST {uri[2]} HTTP/1.0\r\n" \
                f"Host: {uri[0]}\r\n" \
                "Accept: */*\r\n" \
                "Content-Type: application/x-www-form-urlencoded\r\n" \
                f"User-Agent: {self._user_agent}\r\n" \
                "Accept-Encoding: gzip, deflate, br\r\n" \
                f"Content-Length: {len(body)}\r\n" \
                f"Connection: close\r\n\r\n{body}\r\n\r\n"
        self._sock.send(bytes(query, "ISO-8859-1"))
        return self.get_response()

    def head(self, uri):
        query = f"HEAD {uri[2]} HTTP/1.0\r\n" \
                f"Host: {uri[0]}\r\n" \
                f"User-Agent: {self._user_agent}\r\n" \
                "Accept: */*\r\n" \
                "Connection: close\r\n\r\n"
        self._sock.send(bytes(query, "ISO-8859-1"))
        return self.get_response()

    def get_response(self):
        response = []
        while True:
            data = self._sock.recv(1024)
            print(data.decode())
            if not data:
                break
            response.append(data)
        return response

    def parse_response(self, mode: str, response: list):
        if mode == "body":
            for line in response:
                if b"\r\n\r\n" in line:

def main():
    parser = argparse.ArgumentParser()
    methods = parser.add_mutually_exclusive_group()
    parser.add_argument("url", type=str, help="Ссылка на ресурс в формате:")
    parser.add_argument("-a", "--agent", type=str, help="Указать свой USER_AGENT", default="Mozilla/5.0")
    parser.add_argument("-m", "--mode", type=str, choices=["all", "body"],
                        help="Режим вывода ответа от сервера", default="all")
    methods.add_argument("-p", "--params", type=str, help="Указать GET-параметры", default="")
    methods.add_argument("-d", "--data", type=str, help="Отправить данные методом POST", default="")
    methods.add_argument("-I", "--head", action="store_true", help="Отправить запрос при помощи метода HEAD")
    cmd_args = parser.parse_args()
    Client(cmd_args)

if __name__ == '__main__':
    main()
