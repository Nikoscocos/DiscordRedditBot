# Discord Reddit Bot
A bot for discord using discord.py that can display a random post from a subreddit using !reddit &lt;sub>. The name is as such as the bot started off just being able to post pictures from the /r/rule34 sub.

## Changelog
### 10/10/2017
* Updated code to Python 3.6 (@asyncio.coroutine -> async def) (yield from -> await).
* Organised code to comply more with PEP 8.
* Implemented an actual logging system using the logging module.
* Started to implement MySQL to log the servers the bot is connected to.
* Changed all strings to use .format() rather than string concatenation.
* Added commands:
  * !settings / !set - Access the bots settings for this server (server admin only).
  * !super_secret_cmd - Move the bot into the channel of the command sender and say a message using TTS that comes after this command (currently only usable by my own Discord account).
  * die - Kill the bot's process (only usable by my Discord account).
* The bot now detects if 'xd' was in a message and if it was, the bot sends an 'xD' back.
* The bot randomly reacts to messages using one of the emojis on the server where the message was sent.

### 02/07/2017
* Added ConfigParser so all the variables that would change per used can now just be changed in the config file (without needing to change the main script).
* I'm using a module called defusedxml to initally parse the XML file incase something such as an XML bomb slipped through into the file.
* Added a limit (20 characters) on the !reddit &lt;sub> as subreddits cannot have a name above 20 characters so there's no point processing the command.
* Added a few blank functions that will be the MySQL integration when I bother to get around to it.
* Added two more random responses that the bot sends 1-30 minutes after receiving a message.
 
### 20/06/2017
 * Added comments to easily understand what each part of the program is doing.
 * Organised the code into sections.
 * Added the ability to look up the statistics of a player using !stats <playername>.
 * The bot is no longer case sensitive in terms of commands.
 * Added a help command (!gay) to show how to use the bot.
 * Added a debug mode, that, when enabled, will produce a verbose output to the console.
 * Added two more random responses that the bots sends 1-30 minutes after receiving a message.
