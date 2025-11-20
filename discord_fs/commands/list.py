from ..utils import get_size_format, decode, print_table_header, print_table_row, get_terminal_size
from ..api import load_file_index, get_file_index

def list_files(args):
    load_file_index()
    file_index = get_file_index()

    formatting, maxwidth = print_table_header()
    total_size = 0

    for i, values in enumerate(file_index.values()):
        filename = decode(values["filename"])
        total_size += values["size"]
        print_table_row(i + 1, filename, values["size"], formatting, maxwidth)

    terminal_size = get_terminal_size()
    max_width = min(120, terminal_size[0])
    print("-" * max_width)
    print(f"Total storage used: {get_size_format(total_size)}")
