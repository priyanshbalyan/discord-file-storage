import requests
import json
import sys
import os
import io
import re
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
def getSizeFormat(size):
    unit = ["TB", "GB", "MB", "KB", "B"]
    while size / 1024 > 1:
        size /= 1024.0
        unit.pop()

    return "%.*f %s" % (2, size, unit[-1])


def loadFileIndex():
    response = requests.get(BASE_URL + CHANNEL_ID + "/messages", headers=headers)
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

    f = open(INDEX_FILE, "w")
    response = requests.get(url)

    f.write(response.text)
    f.close()

    return last_message["id"]


def getFileIndex():
    try:
        f = open(INDEX_FILE, "r")
        data = f.read()
        f.close()
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


def printTableHeader():
    terminal_size = os.get_terminal_size()

    maxwidth = min(120, terminal_size[0]) - 22
    formatting = "%-" + str(maxwidth) + "s   %-10s   %-5s"

    print(formatting % ("Filename", "Size", "ID"))
    print("-" * maxwidth + "   " + "-" * 9 + "   " + "-" * 5)
    return formatting, maxwidth


def printTableRow(number, filename, size, formatting, maxwidth):
    if len(filename) > maxwidth:
        line = filename[maxwidth:]
        print(
            formatting % (filename[:maxwidth], getSizeFormat(size), "#" + str(number))
        )
        while line:
            print(line[:maxwidth])
            line = line[maxwidth:]
    else:
        print(formatting % (filename, getSizeFormat(size), "#" + str(number)))


def listFiles(args):
    loadFileIndex()
    file_index = getFileIndex()

    formatting, maxwidth = printTableHeader()

    for i, values in enumerate(file_index.values()):
        filename = decode(values["filename"])
        printTableRow(i + 1, filename, values["size"], formatting, maxwidth)


def findFile(args):
    loadFileIndex()
    file_index = getFileIndex()

    results = []
    for i, values in enumerate(file_index.values()):
        filename = decode(values["filename"]).lower()
        if " ".join(args).lower() in filename:
            results.append((i + 1, filename, values["size"]))

    if len(results) > 0:
        formatting, maxwidth = printTableHeader()
        for result_num, result_filename, result_size in results:
            printTableRow(
                result_num, result_filename, result_size, formatting, maxwidth
            )
    else:
        print("No matching files found in the server.")


def getTotalChunks(size):
    if size / CHUNK_SIZE > 1:
        return size // CHUNK_SIZE + 1
    return 1


def updateFileIndex(index_id, file_index):
    f = open(INDEX_FILE, "w")
    f.write(json.dumps(file_index))
    f.close()

    files = [["", [INDEX_FILE, open(INDEX_FILE, "rb")]]]

    # deleting existing index file on the channel
    if index_id:
        print("Deleting old index file")
        response = requests.delete(
            BASE_URL + CHANNEL_ID + "/messages/" + index_id, headers=headers
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
        BASE_URL + CHANNEL_ID + "/messages", headers=headers, files=files
    )
    if response.status_code != 200:
        print("An error occurred while updating index:", response.text)
    print("Done.")


def showProgressBar(iteration, total):
    decimals = 2
    length = min(120, os.get_terminal_size()[0]) - 40
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * (iteration) // total)
    bar = "#" * filled_length + "-" * (length - filled_length - 1)
    print(f"\rProgress: {bar} {iteration}/{total} ({percent}%) Complete", end="")
    if iteration == total:
        print()


def uploadFile(args):
    message_id = loadFileIndex()
    try:
        f = open(args[0], "rb")
    except FileNotFoundError as err:
        print(err)
        sys.exit()

    file_index = getFileIndex()

    size = os.path.getsize(args[0])
    filename = os.path.basename(args[0])
    total_chunks = getTotalChunks(size)

    if encode(filename) in file_index:
        print("File already uploaded.")
        sys.exit()

    print("File Name: ", filename)
    print("File Size: ", getSizeFormat(size))
    print("Chunks to be created: ", total_chunks)
    print("Uploading...")

    urls = []
    for i in range(total_chunks):
        showProgressBar(i + 1, total_chunks)
        chunk = io.BytesIO(f.read(CHUNK_SIZE))  # Read file in 8MB chunks
        files = [["", [encode(filename) + "." + str(i), chunk]]]

        response = requests.post(
            BASE_URL + CHANNEL_ID + "/messages", headers=headers, files=files
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
    updateFileIndex(message_id, file_index)
    f.close()


def downloadFile(args):
    index = (int(args[0][1:]) if args[0][0] == "#" else int(args[0])) - 1
    loadFileIndex()
    file_index = getFileIndex()
    filelist = list(file_index.items())
    if index >= len(filelist):
        print("Invalid ID provided")
        sys.exit()

    print("Downloading...")

    og_name, file = filelist[index]
    filename = decode(file["filename"])
    os.makedirs(os.path.dirname("downloads/" + filename), exist_ok=True)
    f = open("downloads/" + filename, "wb")

    file_regex = r"&|\+|\(|\)|\[|\]|@|\–|'|,"

    for i, values in enumerate(file["urls"]):
        message_id, attachment_id = values
        url = (
            CDN_BASE_URL
            + attachment_id
            + "/"
            + re.sub(file_regex, "", og_name).replace(" ", "_").replace("__", "_")
            + "."
            + str(i)
        )
        response = requests.get(url)  # file attachments are public
        if response.status_code != 200:
            print(
                "An error occurred while downloading the file:",
                response.status_code,
                response.text,
            )
            sys.exit()
        showProgressBar(i + 1, len(file["urls"]))
        f.write(response.content)

    f.close()
    print("Download complete.")


def deleteFile(args):
    index = (int(args[0][1:]) if args[0][0] == "#" else int(args[0])) - 1
    index_message_id = loadFileIndex()

    file_index = getFileIndex()
    file_list = list(file_index.values())
    if index >= len(file_list):
        print("Invalid ID provided")
        sys.exit()

    file = file_list[index]
    message_ids = [i[0] for i in file["urls"]]
    print("Deleting...")

    for i in range(len(message_ids)):
        response = requests.delete(
            BASE_URL + CHANNEL_ID + "/messages/" + message_ids[i], headers=headers
        )
        if response.status_code != 204:
            print(
                "An error occurred while deleting file:",
                response.status_code,
                response.text,
            )
            sys.exit()

        showProgressBar(i + 1, len(message_ids))
        sleep(1)

    del file_index[file["filename"]]
    updateFileIndex(index_message_id, file_index)
    print("Deleted " + decode(file["filename"]) + ".")


def renameFile(args):
    message_id = loadFileIndex()
    file_index = getFileIndex()

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
    print("Size: ", getSizeFormat(file["size"]))
    rename_text = input("Enter new file name: ")
    file["filename"] = encode(rename_text)
    file_index[filename] = {"filename": encode(rename_text), "size": size, "urls": urls}
    updateFileIndex(message_id, file_index)
    print("File renamed")


def init():
    commands = [
        {
            "alias": ["-l", "-list"],
            "function": listFiles,
            "minArgs": 0,
            "syntax": "-l",
            "desc": "Lists all the file information that has been uploaded to the server.",
        },
        {
            "alias": ["-u", "-upload"],
            "function": uploadFile,
            "minArgs": 1,
            "syntax": "-u path/to/file",
            "desc": "Uploads a file to the server. The full file directory is taken in for the argument.",
        },
        {
            "alias": ["-d", "-download"],
            "function": downloadFile,
            "minArgs": 1,
            "syntax": "-d #ID",
            "desc": "Downloads a file from the server. An #ID is taken in as the file identifier",
        },
        {
            "alias": ["-del", "-delete"],
            "function": deleteFile,
            "minArgs": 1,
            "syntax": "-del #ID",
            "desc": "Deletes a file from the server. An #ID is taken in as the file identifier",
        },
        {
            "alias": ["-f", "-find"],
            "function": findFile,
            "minArgs": 1,
            "syntax": "-f text_to_search",
            "desc": "Finds files with matching text",
        },
        {
            "alias": ["-r", "-rename"],
            "function": renameFile,
            "minArgs": 1,
            "syntax": "-r #ID",
            "desc": "Rename a file in the server. An #ID is taken in as the file identifier",
        },
    ]

    global TOKEN, CHANNEL_ID, headers, CDN_BASE_URL

    try:
        f = open(".env", "r")
        TOKEN = f.readline().split("=")[1].strip()
        CHANNEL_ID = f.readline().split("=")[1].strip()
        f.close()
    except FileNotFoundError or IndexError:
        TOKEN = input("Enter bot token to be used: ")
        CHANNEL_ID = input("Enter discord channel id to be used to store files: ")
        f = open(".env", "w")
        f.write("TOKEN=" + TOKEN + "\n" + "CHANNEL_ID=" + CHANNEL_ID)
        f.close()

    headers = {"Authorization": "Bot " + TOKEN}
    CDN_BASE_URL = "https://cdn.discordapp.com/attachments/" + CHANNEL_ID + "/"

    args = sys.argv
    if len(args) == 1:
        print("Usage: python " + os.path.basename(__file__) + " [command] (target)")
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
