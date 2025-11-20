from ..utils import decode, print_table_header, print_table_row
from ..api import load_file_index, get_file_index

def find_file(args):
    load_file_index()
    file_index = get_file_index()

    results = []
    for i, values in enumerate(file_index.values()):
        filename = decode(values["filename"]).lower()
        if " ".join(args).lower() in filename:
            results.append((i + 1, filename, values["size"]))

    if len(results) > 0:
        formatting, maxwidth = print_table_header()
        for result_num, result_filename, result_size in results:
            print_table_row(
                result_num, result_filename, result_size, formatting, maxwidth
            )
    else:
        print("No matching files found in the server.")
