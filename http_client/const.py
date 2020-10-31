HEADER_EXPR = r"[a-zA-z\-]+"
STARTING_LINE = (
    r"(?P<proto>HTTP/1\.[01]) (?P<code>\d{3})(?P<phrase>[ \w]*)"
)
BUFFER_SIZE = 1024
