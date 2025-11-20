import sys
import os
import argparse
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
            sys.exit(0)

    parser = argparse.ArgumentParser(description="Discord File Storage CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", aliases=["l"], help="Lists all files uploaded to the server")
    list_parser.set_defaults(func=list_files)

    # Upload command
    upload_parser = subparsers.add_parser("upload", aliases=["u"], help="Uploads a file to the server")
    upload_parser.add_argument("file", help="Path to the file to upload")
    upload_parser.set_defaults(func=upload_file)

    # Download command
    download_parser = subparsers.add_parser("download", aliases=["d"], help="Downloads a file from the server")
    download_parser.add_argument("id", nargs="+", help="ID(s) of the file(s) to download (e.g., 1 or #1)")
    download_parser.set_defaults(func=download_file)

    # Delete command
    delete_parser = subparsers.add_parser("delete", aliases=["del"], help="Deletes a file from the server")
    delete_parser.add_argument("id", nargs="+", help="ID(s) of the file(s) to delete (e.g., 1 or #1)")
    delete_parser.set_defaults(func=delete_file)

    # Find command
    find_parser = subparsers.add_parser("find", aliases=["f"], help="Finds files with matching text")
    find_parser.add_argument("query", nargs="+", help="Text to search for")
    find_parser.set_defaults(func=find_file)

    # Rename command
    rename_parser = subparsers.add_parser("rename", aliases=["r"], help="Renames a file in the server")
    rename_parser.add_argument("id", help="ID of the file to rename (e.g., 1 or #1)")
    rename_parser.set_defaults(func=rename_file)

    # Parse arguments
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Preprocess sys.argv to support legacy flags
    # Map legacy flags to new subcommands
    legacy_map = {
        "-l": "list", "-list": "list",
        "-u": "upload", "-upload": "upload",
        "-d": "download", "-download": "download",
        "-del": "delete", "-delete": "delete",
        "-f": "find", "-find": "find",
        "-r": "rename", "-rename": "rename"
    }
    
    # Preprocess sys.argv to support legacy flags
    if len(sys.argv) > 1:
        if sys.argv[1] in legacy_map:
            sys.argv[1] = legacy_map[sys.argv[1]]

    args = parser.parse_args()
    
    if hasattr(args, "func"):
        try:
            args.func(args)
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        parser.print_help()

if __name__ == "__main__":
    init()
