import sys
from ..utils import get_size_format, encode, decode
from ..api import load_file_index, get_file_index, update_file_index

def rename_file(args):
    message_id = load_file_index()
    file_index = get_file_index()

    index = (int(args[0][1:]) if args[0][0] == "#" else int(args[0])) - 1
    filelist = list(file_index.values())
    if index >= len(filelist):
        print("Invalid ID provided")
        sys.exit()

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
