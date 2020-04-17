class UrlParsingError(Exception):
    def __init__(self, text: str, url: str):
        self.message = text
        self.wrong_url = url

    def __str__(self):
        return f"{self.message} {self.wrong_url}"


class HeaderFormatError(Exception):
    def __init__(self, text: str, header: str):
        self.message = text
        self.wrong_header = header

    def __str__(self):
        return f"{self.message} '{self.wrong_header}'"