import os
import math
import time
from typing import Callable, Any, Type, Iterable
from .config import CHUNK_SIZE

def with_retry(
    func: Callable,
    max_retries: int = 2,
    delay: float = 2.0,
    exceptions: Iterable[Type[Exception]] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
) -> Any:
    """
    Executes a function with a retry mechanism.
    
    :param func: The function to execute.
    :param max_retries: Number of retry attempts.
    :param delay: Delay between retries in seconds.
    :param exceptions: Tuple of exceptions to catch and retry on.
    :param on_retry: Optional callback function called before each retry.
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                if on_retry:
                    on_retry(attempt + 1, e)
                time.sleep(delay)
            else:
                raise last_exception


def get_size_format(size: int) -> str:
    unit = ["TB", "GB", "MB", "KB", "B"]
    while size / 1024 > 1:
        size /= 1024.0
        unit.pop()

    return "%.*f %s" % (2, size, unit[-1])

# reversible rot13 hash
def encode(string: str) -> str:
    encoded = ""
    for i in string:
        start, end = [ord("a"), ord("z")] if i.islower() else [ord("A"), ord("Z")]
        if i.isalpha():
            if ord(i) + 13 <= end:
                encoded += chr(ord(i) + 13)
            else:
                encoded += chr(start + abs(end - 13 - ord(i)) - 1)
        else:
            encoded += i
    return encoded

def decode(encoded: str) -> str:
    decoded = ""
    for i in encoded:
        start, end = [ord("a"), ord("z")] if i.islower() else [ord("A"), ord("Z")]
        if i.isalpha():
            if ord(i) - 13 >= start:
                decoded += chr(ord(i) - 13)
            else:
                decoded += chr(end - start + ord(i) - 13 + 1)
        else:
            decoded += i
    return decoded

def get_terminal_size() -> os.terminal_size:
    try:
        return os.get_terminal_size()
    except OSError:
        return os.terminal_size((80, 24))

def print_table_header() -> tuple[str, int]:
    terminal_size = get_terminal_size()

    max_width = min(120, terminal_size[0]) - 22
    formatting = f"%-{str(max_width)}s   %-10s   %-5s"

    print(formatting % ("Filename", "Size", "ID"))
    print(f"{'-' * max_width}   {'-' * 9}   {'-' * 5}")
    return formatting, max_width

def print_table_row(number: int, filename: str, size: int, formatting: str, max_width: int) -> None:
    if len(filename) > max_width:
        line = filename[max_width:]
        print(
            formatting % (filename[:max_width], get_size_format(size), "#" + str(number))
        )
        while line:
            print(line[:max_width])
            line = line[max_width:]
    else:
        print(formatting % (filename, get_size_format(size), "#" + str(number)))

def get_total_chunks(size: int) -> int:
    return math.ceil(size / CHUNK_SIZE)

def show_progress_bar(iteration: int, total: int) -> None:
    decimals = 2
    length = min(120, get_terminal_size()[0]) - 40
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * (iteration) // total)
    bar = f"{'#' * filled_length}{'-' * (length-filled_length - 1)}"
    print(f"\rProgress: {bar} {iteration}/{total} ({percent}%) Complete", end="")
    if iteration == total:
        print()
