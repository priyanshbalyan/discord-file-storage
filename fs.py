import requests
import json
import sys
import os
import io
import re
import random
from time import sleep

# USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36'

CHANNEL_ID = ''
TOKEN = ''
CDN_BASE_URL = ''
headers = {}

BASE_URL = 'https://discord.com/api/v9/channels/'
INDEX_FILE = 'index.txt'
CHUNK_SIZE = 8 * 1000 * 1000 # Discord 8MB file limit


def getSizeFormat(size):
    unit = ['TB', 'GB', 'MB', 'KB', 'B']
    while size / 1024 > 1:
        size /= 1024.0
        unit.pop()

    return "%.*f %s" % (2, size, unit[-1])


def loadFileIndex():
    response = requests.get(BASE_URL + CHANNEL_ID + '/messages', headers=headers)
    if response.status_code != 200:
        print('An error occured while loading index: ', response.status_code, response.text)
        sys.exit()
    if len(response.json()) < 1:
        print('No index file found')
        return

    lastMessage = response.json()[0]
    file = lastMessage['attachments'][0]
    filename = file['filename']
    url = file['url']

    if filename != INDEX_FILE:
        print('No index file found')
        return

    f = open(INDEX_FILE, 'w')
    response = requests.get(url)

    f.write(response.text)
    f.close()
    
    return lastMessage['id']
    

def getFileIndex():
    try: 
        f = open(INDEX_FILE, 'r')
        data = f.read()
        f.close()
        return json.loads(data)
    except FileNotFoundError:
        return dict()


# reversible rot13 hash
def encode(string):
    encoded = ''
    for i in string:
        start, end = [ord('a'), ord('z')] if i.islower() else [ord('A'), ord('Z')]
        if i.isalpha():
            if ord(i) + 13 <= end:
                encoded += chr(ord(i) + 13)
            else:
                encoded += chr(start + abs(end - 13 - ord(i)) - 1)
        else:
            encoded += i
    return encoded


def decode(encoded):
    decoded = ''
    for i in encoded:
        start, end = [ord('a'), ord('z')] if i.islower() else [ord('A'), ord('Z')]
        if i.isalpha():
            if ord(i) - 13 >= start:
                decoded += chr(ord(i) - 13)
            else:
                decoded += chr(end - start + ord(i) - 13 + 1)
        else:
            decoded += i
    return decoded

def listFiles(args):
    loadFileIndex()
    fileindex = getFileIndex()
    
    terminalsize = os.get_terminal_size()
    
    maxwidth = min(120, terminalsize[0]) - 22
    formatting = '%-' + str(maxwidth) + 's   %-10s   %-5s'

    print(formatting % ('Filename', 'Size',  'ID'))
    print('-'* maxwidth + '   ' + '-'*9 + '   ' + '-'*5)

    for i, values in enumerate(fileindex.values()):
        filename = decode(values['filename'])
        if len(filename) > maxwidth:
            line = filename[maxwidth:]
            print(formatting % (filename[:maxwidth], getSizeFormat(values['size']), '#' + str(i+1)))
            while line:
                print(line[:maxwidth])
                line = line[maxwidth:]
        else:
            print(formatting % (filename, getSizeFormat(values['size']), '#' + str(i+1)))
        

def getTotalChunks(size):
    if size/CHUNK_SIZE > 1:
        return size // CHUNK_SIZE + 1
    return 1


def updateFileIndex(indexid, fileindex):
    f = open(INDEX_FILE, 'w')
    f.write(json.dumps(fileindex))
    f.close()
    
    files=[['', [INDEX_FILE, open(INDEX_FILE, 'rb')]]]
    
    # deleting existing index file on the channel
    if indexid:
        print('Deleting old index file')
        response = requests.delete(BASE_URL + CHANNEL_ID + '/messages/' + indexid, headers=headers)
        if response.status_code != 204:
            print('An error occured while deleting old index file:', response.status_code, response.text)
    
    # Uploading new update index file
    print('Uploading new updated index file')
    response = requests.post(BASE_URL + CHANNEL_ID + '/messages', headers=headers, files=files)
    if response.status_code != 200:
        print('An error occured while updating index:', response.text)
    print('Done.')


def showProgressBar(iteration, total):
    decimals = 2
    length = min(120, os.get_terminal_size()[0]) - 40
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledlength = int(length * (iteration)//total)
    bar = '#' * filledlength + '-' * (length - filledlength - 1)
    print(f'\rProgress: {bar} {iteration}/{total} ({percent}%) Complete', end = '')
    if iteration == total:
        print()


def uploadFile(args):
    messageid = loadFileIndex()
    try:
        f = open(args[0], 'rb')
    except FileNotFoundError as err:
        print(err)
        sys.exit()
    
    fileindex = getFileIndex()

    size = os.path.getsize(args[0])
    filename = os.path.basename(args[0])
    totalchunks = getTotalChunks(size)
    
    if encode(filename) in fileindex:
        print('File already uploaded.')
        sys.exit()

    print('File Name: ', filename)
    print('File Size: ', getSizeFormat(size))
    print('Chunks to be created: ', totalchunks)
    print('Uploading...')
    
    urls = []
    for i in range(totalchunks):
        showProgressBar(i+1, totalchunks)
        chunk = io.BytesIO(f.read(CHUNK_SIZE)) # Read file in 8MB chunks
        files = [['', [encode(filename) + '.' + str(i), chunk]]]

        response = requests.post(BASE_URL + CHANNEL_ID + '/messages', headers=headers, files=files)
        if response.status_code != 200:
            print('Error encountered while uploading file:', response.text)
            sys.exit()
            
        message = response.json()
        urls.append([message['id'], message['attachments'][0]['id']]) # message_id, attachment_id pair

    print('File uploaded')

    fileindex[encode(filename)] = {
        'filename': encode(filename),
        'size': size,
        'urls': urls
    }    
    updateFileIndex(messageid, fileindex)
    f.close()


def downloadFile(args):
    index = (int(args[0][1:]) if args[0][0] == '#' else int(args[0])) - 1
    loadFileIndex()
    fileindex = getFileIndex()
    filelist = list(fileindex.values())
    if index >= len(filelist):
        print('Invalid ID provided')
        sys.exit()

    print('Downloading...')

    file = filelist[index]
    filename = decode(file['filename'])
    os.makedirs(os.path.dirname("downloads/" + filename), exist_ok=True)
    f = open('downloads/' + filename, 'wb')

    for i, values in enumerate(file['urls']):
        messageid, attachmentid = values
        url = CDN_BASE_URL + attachmentid + '/' + re.sub(r' |&|\+', '', file['filename']) + '.' + str(i)
        response = requests.get(url) #file attachments are public
        if response.status_code != 200:
            print('An error occured while downloading the file:', response.status_code, response.text)
            sys.exit()
        showProgressBar(i+1, len(file['urls']))
        f.write(response.content)

    f.close()
    print('Donwload complete.')


def deleteFile(args):
    index = (int(args[0][1:]) if args[0][0] == '#' else int(args[0])) - 1
    indexmessageid = loadFileIndex()
    
    fileindex = getFileIndex()
    filelist = list(fileindex.values())
    if index >= len(filelist):
        print('Invalid ID provided')
        sys.exit()

    file = filelist[index]
    messageids = [i[0] for i in file['urls']]
    print('Deleting...')
    #bulk delete messages in 200 batches
    for i in range(0, len(messageids), 100):
        if len(messageids[i:i+100]) == 1:
            response = requests.delete(BASE_URL + CHANNEL_ID + '/messages/' + messageids[i], headers=headers)
        else:
            deleteHeaders = {'Authorization': 'Bot ' + TOKEN, 'Content-Type': 'application/json' }
            payload = json.dumps({ 'messages': messageids[i:i+100] })
            response = requests.post(BASE_URL + CHANNEL_ID + '/messages/bulk-delete', headers=deleteHeaders, data=payload)
        
        if response.status_code != 204:
            print('An error occured while deleting file:', response.status_code, response.text)
            sys.exit()
        sleep(3)

    del fileindex[file['filename']]
    updateFileIndex(indexmessageid, fileindex)
    print('Deleted ' + decode(file['filename']) + '.')


def init():
    commands = [
        {
            'alias': ['-l', '-list'],
            'function': listFiles,
            'minArgs': 0,
            'syntax': '-l',
            'desc': 'Lists all the file informations that has been uploaded to the server.'
        },
        {
            'alias': ['-u', '-upload'],
            'function': uploadFile,
            'minArgs': 1,
            'syntax': '-u path/to/file',
            'desc': 'Uploads a file to the server. The full file directory is taken in for the argument.'
        },
        {
            'alias': ['-d', '-download'],
            'function': downloadFile,
            'minArgs': 1,
            'syntax': '-d #ID',
            'desc': 'Downloads a file from the server. An #ID is taken in as the file identifier'
        },
        {
            'alias': ['-del', '-delete'],
            'function': deleteFile,
            'minArgs': 1,
            'syntax': '-del #ID',
            'desc': 'Deletes a file from the server. An #ID is taken in as the file identifier'
        }
    ]

    global TOKEN, CHANNEL_ID, headers, CDN_BASE_URL

    try:
        f = open('.env', 'r')
        TOKEN = f.readline().split('=')[1].strip()
        CHANNEL_ID = f.readline().split('=')[1].strip()
        f.close()
    except FileNotFoundError or IndexError:
        TOKEN = input('Enter bot token to be used: ')
        CHANNEL_ID = input('Enter discord channel id to be used to store files: ')
        f = open('.env', 'w')
        f.write('TOKEN=' + TOKEN + '\n' + 'CHANNEL_ID=' + CHANNEL_ID)
        f.close()

    headers = {'Authorization': 'Bot ' + TOKEN }
    CDN_BASE_URL = 'https://cdn.discordapp.com/attachments/' + CHANNEL_ID + '/'

    args = sys.argv
    if len(args) == 1:
        print('Usage: python ' + os.path.basename(__file__) + ' [command] (target)')
        print('COMMANDS:')
        for cmd in commands:
            print('[%s] :: %s' % (', '.join(cmd['alias']), cmd['desc']))
        sys.exit()
    else:
        if not TOKEN:
            print('No token provided')
            sys.exit()
        if not CHANNEL_ID:
            print('Not channel id provided')
            sys.exit()

    for cmd in commands:
        if args[1] in cmd['alias']:
            if len(args) < cmd['minArgs'] + 2:
                print('Description: ', cmd['desc'])
                print('Syntax: python', sys.argv[0], cmd['syntax'])
                sys.exit()
            else:
                cmd['function'](args[2:])
            break


init()
