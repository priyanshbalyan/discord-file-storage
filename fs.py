import requests
import json
import sys
import os
import io
from time import sleep

# USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36'

# Add your discord channel id here
CHANNEL_ID = ""
# Add your discord bot token here
TOKEN = ""
CDN_BASE_URL = ""
headers = {}

BASE_URL = "https://discord.com/api/v9/channels/"
INDEX_FILE = "index.txt"
CHUNK_SIZE = 8 * 1000 * 1000  # Discord 8MB file limit


# Get size unit text from number of bytes
def get_size_format(size):
    unit = ["TB", "GB", "MB", "KB", "B"]
    while size / 1024 > 1:
        size /= 1024.0
        unit.pop()

    return "%.*f %s" % (2, size, unit[-1])


def load_file_index():
    response = requests.get(f"{BASE_URL}{CHANNEL_ID}/messages?limit=1", headers=headers)
    if response.status_code != 200:
        print(
            "An error occurred while loading index: ",
            response.status_code,
            response.text,
        )
        sys.exit()
    if len(response.json()) < 1:
        print("No index file found")
        return

    last_message = response.json()[0]
    file = last_message["attachments"][0]
    filename = file["filename"]
    url = file["url"]

    if filename != INDEX_FILE:
        print("No index file found")
        return

    with open(INDEX_FILE, "w") as f:
        response = requests.get(url)
        f.write(response.text)

    return last_message["id"]


def get_file_index():
    try:
        with open(INDEX_FILE, "r") as f:
            data = f.read()
        return json.loads(data)
    except FileNotFoundError:
        return dict()


# reversible rot13 hash
def encode(string):
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


def decode(encoded):
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


def print_table_header():
    terminal_size = os.get_terminal_size()

    max_width = min(120, terminal_size[0]) - 22
    formatting = f"%-{str(max_width)}s   %-10s   %-5s"

    print(formatting % ("Filename", "Size", "ID"))
    print(f"{'-' * max_width}   {'-' * 9}   {'-' * 5}")
    return formatting, max_width


def print_table_row(number, filename, size, formatting, max_width):
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


def list_files(args):
    load_file_index()
    file_index = get_file_index()

    formatting, maxwidth = print_table_header()
    total_size = 0

    for i, values in enumerate(file_index.values()):
        filename = decode(values["filename"])
        total_size += values["size"]
        print_table_row(i + 1, filename, values["size"], formatting, maxwidth)

    terminal_size = os.get_terminal_size()
    max_width = min(120, terminal_size[0])
    print("-" * max_width)
    print(f"Total storage used: {get_size_format(total_size)}")


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


def get_total_chunks(size):
    if size / CHUNK_SIZE > 1:
        return size // CHUNK_SIZE + 1
    return 1


def update_file_index(index_id, file_index):
    with open(INDEX_FILE, "w") as f:
        f.write(json.dumps(file_index))

    files = [["", [INDEX_FILE, open(INDEX_FILE, "rb")]]]

    # deleting existing index file on the channel
    if index_id:
        print("Deleting old index file")
        response = requests.delete(
            f"{BASE_URL}{CHANNEL_ID}/messages/{index_id}", headers=headers
        )
        if response.status_code != 204:
            print(
                "An error occurred while deleting old index file:",
                response.status_code,
                response.text,
            )

    # Uploading new update index file
    print("Uploading new updated index file")
    response = requests.post(
        f"{BASE_URL}{CHANNEL_ID}/messages", headers=headers, files=files
    )
    if response.status_code != 200:
        print("An error occurred while updating index:", response.text)
    print("Done.")


def show_progress_bar(iteration, total):
    decimals = 2
    length = min(120, os.get_terminal_size()[0]) - 40
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * (iteration) // total)
    bar = f"{'#' * filled_length}{'-' * (length-filled_length - 1)}"
    print(f"\rProgress: {bar} {iteration}/{total} ({percent}%) Complete", end="")
    if iteration == total:
        print()


def upload_file(args):
    message_id = load_file_index()
    try:
        f = open(args[0], "rb")
    except FileNotFoundError as err:
        print(err)
        sys.exit()

    with f:
        file_index = get_file_index()

        size = os.path.getsize(args[0])
        filename = os.path.basename(args[0])
        total_chunks = get_total_chunks(size)

        if encode(filename) in file_index:
            print("File already uploaded.")
            sys.exit()

        print("File Name: ", filename)
        print("File Size: ", get_size_format(size))
        print("Chunks to be created: ", total_chunks)
        print("Uploading...")

        urls = []
        for i in range(total_chunks):
            show_progress_bar(i + 1, total_chunks)
            chunk = io.BytesIO(f.read(CHUNK_SIZE))  # Read file in 8MB chunks
            files = [["", [encode(filename) + "." + str(i), chunk]]]

            response = requests.post(
                f"{BASE_URL}{CHANNEL_ID}/messages", headers=headers, files=files
            )
            if response.status_code != 200:
                print("Error encountered while uploading file:", response.text)
                sys.exit()

            message = response.json()
            urls.append(
                [message["id"], message["attachments"][0]["id"]]
            )  # message_id, attachment_id pair

        print("File uploaded")

        file_index[encode(filename)] = {
            "filename": encode(filename),
            "size": size,
            "urls": urls,
        }
        update_file_index(message_id, file_index)


def download_file(args):
    indices = []
    for arg in args:
        indices.append(int(arg[1:]) if arg[0] == "#" else int(arg) - 1)

    load_file_index()
    file_index = get_file_index()
    filelist = list(file_index.items())

    # file_regex = r"[&+()\[\]@–',]" # Unused

    for index in indices:
        if index >= len(filelist):
            print(f"Invalid ID provided: {index}")
            sys.exit()

        print("Downloading...")

        og_name, file = filelist[index]
        filename = decode(file["filename"])
        os.makedirs(os.path.dirname(f"downloads/{filename}"), exist_ok=True)
        
        with open("downloads/" + filename, "wb") as f:
            for i, values in enumerate(file["urls"]):
                # TODO: Remove attachment_id from index file
                message_id, attachment_id = values

                response = requests.get(f"{BASE_URL}{CHANNEL_ID}/messages/{message_id}", headers=headers)
                if response.status_code != 200:
                    print("An error occurred while loading messages: ", response.status_code, response.text)
                    sys.exit()

                attachments = response.json()['attachments']
                download_url = attachments[0]['url']

                cdnResponse = requests.get(download_url)  # download from url with identification params
                if cdnResponse.status_code != 200:
                    print("An error occurred while downloading the file:", cdnResponse.status_code, cdnResponse.text)
                    sys.exit()

                show_progress_bar(i + 1, len(file["urls"]))
                f.write(cdnResponse.content)

    print("Download complete.")


def delete_file(args):
    index = (int(args[0][1:]) if args[0][0] == "#" else int(args[0])) - 1
    index_message_id = load_file_index()

    file_index = get_file_index()
    file_list = list(file_index.values())
    if index >= len(file_list):
        print("Invalid ID provided")
        sys.exit()

    file = file_list[index]
    message_ids = [i[0] for i in file["urls"]]
    print("Deleting...")

    for i in range(len(message_ids)):
        response = requests.delete(
            f"{BASE_URL}{CHANNEL_ID}/messages/{message_ids[i]}", headers=headers
        )
        if response.status_code != 204:
            print(
                "An error occurred while deleting file:",
                response.status_code,
                response.text,
            )
            sys.exit()

        show_progress_bar(i + 1, len(message_ids))
        sleep(1)

    del file_index[file["filename"]]
    update_file_index(index_message_id, file_index)
    print(f"Deleted {decode(file['filename'])}.")


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


def init():
    commands = [
        {
            "alias": ["-l", "-list"],
            "function": list_files,
            "minArgs": 0,
            "syntax": "-l",
            "desc": "Lists all the file information that has been uploaded to the server.",
        },
        {
            "alias": ["-u", "-upload"],
            "function": upload_file,
            "minArgs": 1,
            "syntax": "-u path/to/file",
            "desc": "Uploads a file to the server. The full file directory is taken in for the argument.",
        },
        {
            "alias": ["-d", "-download"],
            "function": download_file,
            "minArgs": 1,
            "syntax": "-d #ID",
            "desc": "Downloads a file from the server. An #ID is taken in as the file identifier. Provide multiple ids separated by space to download multiple files",
        },
        {
            "alias": ["-del", "-delete"],
            "function": delete_file,
            "minArgs": 1,
            "syntax": "-del #ID",
            "desc": "Deletes a file from the server. An #ID is taken in as the file identifier",
        },
        {
            "alias": ["-f", "-find"],
            "function": find_file,
            "minArgs": 1,
            "syntax": "-f text_to_search",
            "desc": "Finds files with matching text",
        },
        {
            "alias": ["-r", "-rename"],
            "function": rename_file,
            "minArgs": 1,
            "syntax": "-r #ID",
            "desc": "Rename a file in the server. An #ID is taken in as the file identifier",
        },
    ]

    global TOKEN, CHANNEL_ID, headers, CDN_BASE_URL

    try:
        with open(".env", "r") as f:
            TOKEN = f.readline().split("=")[1].strip()
            CHANNEL_ID = f.readline().split("=")[1].strip()
    except (FileNotFoundError, IndexError):
        TOKEN = input("Enter bot token to be used: ")
        CHANNEL_ID = input("Enter discord channel id to be used to store files: ")
        with open(".env", "w") as f:
            f.write(f"TOKEN={TOKEN}\nCHANNEL_ID={CHANNEL_ID}")

    headers = {"Authorization": f"Bot {TOKEN}"}
    CDN_BASE_URL = f"https://cdn.discordapp.com/attachments/{CHANNEL_ID}/"

    args = sys.argv
    if len(args) == 1:
        print(f"Usage: python {os.path.basename(__file__)} [command] (target)")
        print("COMMANDS:")
        for cmd in commands:
            print("[%s] :: %s" % (", ".join(cmd["alias"]), cmd["desc"]))
        sys.exit()
    else:
        if not TOKEN:
            print("No token provided")
            sys.exit()
        if not CHANNEL_ID:
            print("Not channel id provided")
            sys.exit()

    for cmd in commands:
        if args[1] in cmd["alias"]:
            if len(args) < cmd["minArgs"] + 2:
                print("Description: ", cmd["desc"])
                print("Syntax: python", sys.argv[0], cmd["syntax"])
                sys.exit()
            else:
                cmd["function"](args[2:])
            break


init()
