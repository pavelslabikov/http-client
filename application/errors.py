import socket


class APIError(Exception):
    arg: str


class UrlParsingError(APIError):
    def __init__(self, url: str):
        self.arg = url

    def __str__(self):
        return f"Некорректный формат введённой ссылки: {self.arg}"


class HeaderFormatError(APIError):
    def __init__(self, header: str):
        self.arg = header

    def __str__(self):
        return f"Некорректный формат пользовательского заголовка: '{self.arg}'"


class ConnectingError(APIError, socket.gaierror):
    def __init__(self, host: str, port):
        self.arg = f"{host}. Порт: {port}"

    def __str__(self):
        return f"Не удалось подключиться по заданному адресу: {self.arg}"


class IncorrectStartingLineError(APIError):
    def __init__(self, line: str):
        self.arg = line

    def __str__(self):
        return f"Некорректная стартовая строка ответа от сервера: {self.arg}"


