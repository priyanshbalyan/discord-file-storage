import sys
from ..utils import get_size_format, encode, decode
from ..api import load_file_index, get_file_index, update_file_index

def rename_file(args):
    raw_id = args.id
    try:
        index = (int(raw_id[1:]) if raw_id.startswith("#") else int(raw_id)) - 1
    except ValueError:
        print("Invalid ID format")
        return

    message_id = load_file_index()
    file_index = get_file_index()

    filelist = list(file_index.values())
    if index >= len(filelist) or index < 0:
        print("Invalid ID provided")
        return

    file = filelist[index]
    filename = file["filename"]
    size = file["size"]
    urls = file["urls"]
    print("File details:")
    print("Name: ", decode(file["filename"]))
    print("Size: ", get_size_format(file["size"]))
    
    rename_text = input("Enter new file name: ")
    file["filename"] = encode(rename_text)
    file_index[filename] = {"filename": encode(rename_text), "size": size, "urls": urls}
    update_file_index(message_id, file_index)
    print("File renamed")
