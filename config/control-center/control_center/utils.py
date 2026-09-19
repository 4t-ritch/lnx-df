def split_nmcli_line(line: str) -> list[str]:
    fields = []
    buf = []
    escaped = False
    for char in line:
        if escaped:
            buf.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(buf))
            buf = []
        else:
            buf.append(char)
    if escaped:
        buf.append("\\")
    fields.append("".join(buf))
    return fields


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))


def snap_volume(value: float, step: int = 2) -> int:
    return clamp(round(int(value) / step) * step)
