import sys
import os
from .config import load_config, save_config, TOKEN, CHANNEL_ID
from .commands import (
    list_files,
    upload_file,
    download_file,
    delete_file,
    find_file,
    rename_file,
)

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

    load_config()
    
    # Prompt for configuration if missing
    
    from . import config
    
    if not config.TOKEN or not config.CHANNEL_ID:
        try:
            token = input("Enter bot token to be used: ")
            channel_id = input("Enter discord channel id to be used to store files: ")
            save_config(token, channel_id)
            # Reload config to update globals
            load_config()
        except KeyboardInterrupt:
            sys.exit()

    args = sys.argv
    if len(args) == 1:
        print(f"Usage: python {os.path.basename(sys.argv[0])} [command] (target)")
        print("COMMANDS:")
        for cmd in commands:
            print("[%s] :: %s" % (", ".join(cmd["alias"]), cmd["desc"]))
        sys.exit()
    else:
        if not config.TOKEN:
            print("No token provided")
            sys.exit()
        if not config.CHANNEL_ID:
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

if __name__ == "__main__":
    init()
