"""Video / kamera kaynak cozumlemesi."""


def parse_source(src: str) -> str | int:
    if src.isdigit():
        return int(src)
    return src
