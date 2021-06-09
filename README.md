# Discord Storage
Utilize Discord servers as cloud storage!

## Tutorial
#### Setting up the bot/server
Install dependencies with ``pip install -r requirements.txt``
##### 1) Creating the bot
In order for this program to work, you're going to need to create a discord bot so we can connect to the discord API. Go to [this](https://discordapp.com/developers/applications/me) link to create a bot. Make sure to create a user bot and ensure the bot is private. **Keep note of the token and the client ID.**
##### 2) Setting up the server
The bot will need a place to upload files. Create a new discord server, make sure no one else is on it unless you want them to access your files.

##### 3) Adding your bot to the server
To add the bot to the server (assuming your bot isn't public), go to the following link (Needs manage messages permission): https://discordapp.com/oauth2/authorize?client_id={CLIENT_ID}&scope=bot&permissions=11264
Replace {CLIENT_ID} with the client ID you copied earlier.

#### Setting up the program
Clone the repository.
##### 1) Configuration
Run ```python fs.py``` to begin configuration of the bot. When prompted, copy and paste your **token** from when you created your bot. For the channel ID, copy the channel ID with right click on the channel (developer mode must be enabled under appearance on Discord settings to have the option for Copy ID).

*You can delete ```.env``` to reconfigure the program.*
#### Commands
Usage: ```python fs.py [flag] {args}```

```-upload /full_path/file.exe``` The -upload or -u flag and the full file path uploads a file.

```-download {#ID}``` The -download or -d flag and the file id will download a file from the discord server. Refer to the ```-list``` command to see uploaded file codes.

```-list``` The -list or -l flag will list all the file names/sizes/ids uploaded to the discord server.