import datetime
import asyncio
import logging
import random
import time
import os
import discord
import pymysql
import praw

import defusedxml.ElementTree as defusedetree
import xml.etree.ElementTree as etree

from configparser import ConfigParser
from ctypes.util import find_library
from tempfile import TemporaryFile
from time import strftime
from html import escape
from gtts import gTTS

#  from Rule34BotClasses import ConnectedServer

config = ConfigParser()
config.read("rule34_bot.cfg")

xmlfile = config["Data_Logging"]["xml_file"]

discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.DEBUG)
logger = logging.getLogger('r34_bot')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler(config["Data_Logging"]["log_file"], 'a+')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
fh_format = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s', '%y-%m-%d %H:%M:%S')
ch_format = logging.Formatter('%(asctime)s %(levelname)-8s: %(message)s', '%d-%m %H:%M:%S')
fh.setFormatter(fh_format)
ch.setFormatter(ch_format)
# add the handlers to logger
logger.addHandler(fh)
logger.addHandler(ch)
discord_logger.addHandler(fh)
discord_logger.addHandler(ch)

db = pymysql.connect(host=config["MySQL"]["host"],
                     user=config["MySQL"]["user"],
                     password=config["MySQL"]["password"],
                     db=config["MySQL"]["database"],
                     charset='utf8mb4',
                     cursorclass=pymysql.cursors.DictCursor)

reddit = praw.Reddit(client_id=config["Reddit"]["client_id"],
                     client_secret=config["Reddit"]["client_secret"],
                     user_agent=config["Reddit"]["user_agent"])

client = discord.Client()
tree = defusedetree.parse(xmlfile)
root = tree.getroot()

    
#  Sending a random message after a user has entered a command. 

#  This function is triggered whenever someone uses the command !reddit or !rule34.
async def send_random_message(channel): 
    global waitingToSend
    try:
    	waitingToSend
    except:
        waitingToSend = False
    if not waitingToSend: 
        #  If the function has already been run within the past 30 minutes (or less), it will not run again.
        waitingToSend = True
        currentTime = datetime.datetime.now()
        nextHalfHour = random.randrange(30) + 1 #  Choose a random number between 1 and 30
        plannedTime = currentTime + datetime.timedelta(minutes=nextHalfHour) #  Get the date to print to the console.
        logger.info("Job 'choose_random_message' set to execute at {0} (in {1} minutes).".format(plannedTime.strftime('%d/%m/%Y %H:%M:%S'), str(nextHalfHour)))
        await asyncio.sleep(nextHalfHour*60) #  Wait for the amount of minutes in nextHalfHour
        await choose_random_message(channel) #  Execute choose_random_message

        
async def choose_random_message(channel):
    global waitingToSend
    waitingToSend = False #  Make it so send_random_message can be executed again.
    x = random.randrange(5) #  Choose a number between 0 and the number before the number in the brackets.
    logger.info("Time has been reached. Sending message ID: {0}".format(str(x)))
#   if x == 0: #  Choose a random person in the server and say you hate them.
#       i = 0
#       randomUserInServer = random.randrange(channel.server.member_count)
#       for y in channel.server.members:
#           if i == randomUserInServer:
#               await client.send_message(channel, "I'm not gonna lie, I don't really like {0.mention}.".format(y))
#               break
#           else:
#               i += 1
    if x == 1: #  Make the bot perform !r34 to itself.
        await client.send_message(channel, "!r34")
        post = reddit.subreddit('rule34').random()
        await asyncio.sleep(0.6)
        await add_count(client.user, "rule34", True)
        await client.send_message(channel, post.url)
    elif x == 2: #  Make the bot perform !reddit using a random subreddit.
        randomSub = reddit.random_subreddit(nsfw=True)
        logger.info("Retrieving a random NSFW subreddit: {0}".format(randomSub.display_name))
        await client.send_message(channel, "!reddit {0}".format(randomSub.display_name))
        post = randomSub.random()
        await asyncio.sleep(0.6)
        await add_count(client.user, randomSub.display_name, True)
        await client.send_message(channel, post.url)
    elif x == 3: #  Make the bot say some random shit (a title from /r/subredditsimulator).
        post = reddit.subreddit('subredditsimulator').random()
        logger.info("Got post from /r/subredditsimulator: https://www.reddit.com{0}".format(post.permalink))
        await client.send_message(channel, post.title, tts=True)

        
#  Working with MySQL (logging data). 


def mysql_update_user(usrObj):
    pass

    
def mysql_add_count(usrObj, subName, subExists):
    pass

    
def mysql_check_element_exists(userID, subName):
    pass

    
async def refresh_server_list():
    global cached_settings
    cached_settings = {}
    with db.cursor() as cursor:
        cursor.execute("UPDATE `connected_servers` SET `connected` = FALSE")
        db.commit()
        cursor.execute("SELECT `discord_server_id` FROM `connected_servers`")
        servers_in_db = cursor.fetchall()
        for connected_server in client.servers:
            if any(d['discord_server_id'] == int(connected_server.id) for d in servers_in_db):
                cursor.execute("UPDATE `connected_servers` SET `connected` = TRUE WHERE `connected_servers`.`discord_server_id` = {0}".format(connected_server.id))
                db.commit()
                # logger.info("Connected to server {0}".format(connected_server.name))
                cursor.execute("SELECT `enable_random_react`,`enable_random_message` FROM `connected_servers` WHERE `discord_server_id` = {0}".format(connected_server.id))
                cached_settings[connected_server.id] = cursor.fetchone()
            else:
                cursor.execute("""INSERT INTO `discord_bot_reddit`.`connected_servers` (
                    `id`, `discord_server_id`, `discord_server_name`, `connected`, `enable_random_react`, `enable_random_message`
                    ) VALUES (NULL, '{0}', '{1}', '1', '1', '0');""".format(connected_server.id, escape(connected_server.name)))
                db.commit()
                logger.info("Added server {0} to database.".format(connected_server.name))
        print(cached_settings)

        
#  Working with XML (logging data).


async def update_user(usrObj): #  When a user joins or updates their name, update their name in the XML file. If they don't exist, make an element for them.
    for user in root.findall('user'):
        if user.attrib["id"] == str(usrObj.id):
            user.attrib["name"] = escape(usrObj.name)
            tree.write(xmlfile)
            return
    newUser = etree.SubElement(root, "user", {"name": escape(usrObj.name), "id": usrObj.id, "dateAdded": str(int(time.time())), "lastUsed": str(int(time.time()))}) #  if a user doesn't exist, add them to the file
    tree.write(xmlfile) #  Write to the XML file.

    
async def add_count(usrObj, subName, subExists): #  Increase the value of a sub for a user.
    subName = escape(subName) #  Escape the subreddit's name.
    for user in root.findall('user'):
        if user.attrib["id"] == str(usrObj.id):
            currentTime = str(int(time.time()))
            user.attrib["lastUsed"] = currentTime #  Make the lastUsed attribute the current time in epoch.
            if check_element_exists(usrObj.id, subName):
                for sub in user:
                    if sub.attrib["name"] == subName:
                        sub.attrib["val"] = str(int(sub.attrib["val"]) + 1) #  Increase the value of the sub by one.
                        sub.attrib["last"] = currentTime
                        tree.write(xmlfile)
                        return
            else:
                subType = "sub" if subExists else "failedSub" #  If the sub exists, make the element a sub, if it doesn't, make it a failedSub
                newSub = etree.SubElement(user, subType, {"name": subName, "last": currentTime, "val": "1"})
                tree.write(xmlfile)
                return

                
def check_element_exists(userID, subName): #  Check if a sub has already been used by the user.
    for user in root.findall('user'): 
        if user.attrib["id"] == str(userID): #  If the user is equal to the author,
            for sub in user: #  loop through subs.
                if sub.attrib["name"] == subName:
                    return True
    return False #  If the loop didn't return True, return False.

    
#  Displaying the XML data to the user.


async def find_user_top_10_subs(channel, nameToFind): #  Read the XML file and get the subs of the user.
    usersFound = [] #  Make the array to contain all the users matching the search term.
    for user in root.findall('user'):
        if nameToFind.lower() in user.attrib["name"].lower():
            usersFound.append(user) #  If the search term is in the users name, add them to the usersFound array.
    if len(usersFound) == 0: #  If the array is empty, no users matched the search terms.
        logger.warning("No users found.")
        await client.send_message(channel, "```No users found.```") #  Inform the user.
    elif len(usersFound) == 1: #  If one user was found, find their top 10 subs.
        top10Subs = [] #  Make the array to contain all the subs that were found in the users element.
        for sub in usersFound[0]:
            top10Subs.append(sub) #  Add all the subs to the array.
        top10Subs.sort(key=lambda x: int(x.attrib["val"]), reverse=True) #  Sort the subs by the amount of times they were used by the user, with the most used being at top10Subs[0].
        subLeaderboardMsg = "" #  A string that will contain the names and the values of the top 10 items in the array.
        if len(top10Subs) > 0: #  If the array is bigger than 0, then add the subs to the string.
            for sub in top10Subs[:10]: #  Loop through only the first 10 items in the array.
                subLeaderboardMsg += sub.attrib["name"] + " - " + sub.attrib["val"] + "\n"
        else: #  If no items are in the array, the user has not used the bot.
            subLeaderboardMsg = "No data found for this user.\n" #  Inform the user.
        logger.info("Retrieved stats of user '{0}'.".format(usersFound[0].attrib["name"]))
        await client.send_message(channel, "User '{0}':\n```{1}```".format(usersFound[0].attrib["name"], subLeaderboardMsg)) #  Show the user the top 10 subs of the name they requested.
    else: #  If multiple users were found, inform the user.
        userNamesFound = "" #  A string that will contain all the names of the users that matched the search terms.
        for user in usersFound:
            userNamesFound += user.attrib["name"] + "\n"
        logger.warning("Multiple users found.")
        await client.send_message(channel, "Multiple users found: ```\n{0}```".format(userNamesFound))


async def get_top_three_users(channel):
    pass


#  Main Discord interaction.


@client.event
async def on_message(message): #  Event: When the bot sees a message in a channel.
    if message.author == client.user: #  Making sure the bot does not reply to itself.
        return

    if message.content.lower().startswith('!rule34') or message.content.lower().startswith('!r34'):
        sub = reddit.subreddit('rule34')
        post = sub.random() #  Get a random post from the sub /r/rule34.
        logger.info("'{0}' asked for a random post on '/r/rule34': {1}".format(message.author.name, post.url))
        await add_count(message.author, "rule34", True) #  Add 1 to this subreddit value under this user in the XML file.
        # em = discord.Embed(title=post.title, colour=0x6729ad)
        # em.set_proxy_image(url=post.url)
        # em.set_author(name='/u/' + post.author.name, url=post.shortlink)
        # await client.send_message(message.channel, embed=em)
        await client.send_message(message.channel, post.url)
        await send_random_message(message.channel) #  Activate the send_random_message function.

    elif message.content.lower().startswith('!reddit '):
        subToCheck = message.content.split(' ')[1].lower()
        if len(subToCheck) > 20: #  Subreddit names are a max 20 characters in length, so no point searching for one with a longer name.
            await client.send_message(message.channel, "That name is too long for a subreddit. Please try a shorter name.")
            await send_random_message(message.channel)
            return
        try:
            post = reddit.subreddit(subToCheck).random() #  Get a random post from the sub /r/rule34.
            logger.info("'{0}' asked for a random post on '/r/{1}': {2}".format(message.author.name, subToCheck, post.url))
            await add_count(message.author, subToCheck, True) #  Add 1 to this subreddit value under this user in the XML file.
            await client.send_message(message.channel, post.url)
        except Exception as e: #  If the sub doesn't exist (or another error occurs), tell the user.
            await add_count(message.author, subToCheck, False)
            fmt = 'An error occurred while processing this request: ```py\n{0}: {1}\n```'
            await client.send_message(message.channel, fmt.format(type(e).__name__, e))
        await send_random_message(message.channel) #  Activate the send_random_message function.

    elif message.content.lower().startswith('!stats'):
        msgArgs = message.content.split(' ') #  Get the arguments used in the message
        msgArgs.pop(0) #  Remove the first item (the command, !stats)
        nameToFind = escape(" ".join(msgArgs)) #  Convert the name to one with HTML escape codes.
        if len(msgArgs) > 0: #  If the user inputted a name, search for it.
            logger.info("'{0}' searched for the stats of '{1}'.".format(message.author.name, nameToFind))
            await find_user_top_10_subs(message.channel, nameToFind)
        else: #  Else, get the top three users of !r34.
            await get_top_three_users(message.channel)

    elif message.content.lower().startswith('!settings') or message.content.lower().startswith('!set'):
        if message.channel.is_private:
            await client.send_message(message.channel, "```\nYou cannot set server settings in a private session.\n```")
        elif not message.author.server_permissions.administrator:
            await client.send_message(message.channel, "```\nYou do not have permission to use that command.\n```")
        else:
            msgArgs = message.content.split(' ')
            if len(msgArgs) == 1 or msgArgs[1] == "help":
                await client.send_message(message.channel, "```\nSettings -\n\n 1)\n```")
                #return
            elif msgArgs[1].lower() == "show":
                pass
            elif len(msgArgs) == 3:
                pass
            else:
                await client.send_message(message.channel, "```\nUse {0} help to access the help section.\n```".format(msgArgs[0]))
    
    elif message.content.lower().startswith('!clear'):
        return
        logger.info("'{0}' has asked to clear the porn.".format(message.author.name))
        msgArgs = message.content.split(' ')
        msgArgs.pop(0)
        if len(msgArgs) == 0:
            for i in range(0, 5):
                post = reddit.subreddit('aww').random()
                await asyncio.sleep(0.6)
                await client.send_message(message.channel, post.url)
        else:
            for i in range(0, 5):
                try:
                    post = reddit.subreddit(msgArgs[0]).random() #  Get a random post from the sub /r/rule34.
                    await client.send_message(message.channel, post.url)
                except Exception as e: #  If the sub doesn't exist (or another error occurs), tell the user.
                    fmt = 'An error occurred while processing this request: ```py\n{0}: {1}\n```'
                    await client.send_message(message.channel, fmt.format(type(e).__name__, e))
        

    elif message.content.lower().startswith('!gay'):
        logger.info("'{0}' asked for help.".format(message.author.name))
        help_string =  "```\nCommands -\n\n !r34 / !rule34 - a shortcut for '!reddit rule34'. Also the main feature of this bot.\n !reddit <sub> - Sends a random post from a subreddit to the channel.\n !stats <user> - Shows the statistics for that user.\n !stats - Shows the top three users to use !r34.\n !settings / !set - Access the bots settings for this server (server admin only).\n !gay - Access this help.\n\nPlaying !gay reference: https://youtu.be/hUdp1QEcxiY?t=1m40s\n```"
        await client.send_message(message.channel, help_string)
        
    elif message.content.lower().startswith('!super_secret_cmd') and message.author.id == '214470441824288768':
        msgArgs = message.content.split(' ')
        msgArgs.pop(0)
        text_to_say = " ".join(msgArgs)
        if message.author.voice.voice_channel:
            try:
                voice = await client.join_voice_channel(message.author.voice.voice_channel)
            except discord.ClientException:
                await client.send_message(message.channel, "I'm already in a voice channel and you will not make me move >:(.")
                return
            except discord.InvalidArgument:
                await client.send_message(message.channel, "What are you playing at? I can't bloody join that you fool.")
                return
            tts = gTTS(text=text_to_say, lang='en-uk', slow=False)
            temp_file_name = '/tmp/tts_for_server_{0}.mp3'.format(message.server.id)
            tts.save(temp_file_name)
            player = voice.create_ffmpeg_player(temp_file_name, after=lambda: my_after(player, voice, temp_file_name))
            logger.info("Playing Text-To-Speech.")
            player.start()
            def my_after(player, voice, temp_file_name):
                logger.info("TTS playing finished. Closing player and deleting temp file...")
                player.stop()
                os.remove(temp_file_name)
                logger.info("Temporary file deleted. Disconnecting...")
                # voice.disconnect()
                # print("Disconnected.")
                # coro = voice.disconnect()
                # fut = asyncio.run_coroutine_threadsafe(coro, client.loop)
                # try:
                #      fut.result()
                #      print('Disconnected.')
                # except:
                #      print('[-] An error has occured.')
    
    elif 'xd' in message.content.lower():
        # emoji_list = message.server.emojis
        # reaction_to_message = emoji_list[random.randint(0, len(emoji_list)-1)] if len(emoji_list) else u"\U0001F629"
        # currentTime = datetime.datetime.now()
        # logger.info("Adding random react to a message sent by '{0}' on server '{1}'.".format(message.author.name, message.server.name))
        # try:
        #     await client.add_reaction(message, reaction_to_message)
        # except discord.HTTPException as e:
        #     logger.error("There was an error when attempting to react to a message - {0}: {1}".format(type(e).__name__, e))
        # await client.add_reaction(message, reaction_to_message)
        await client.send_message(message.channel, "xD")
    
    elif message.content.lower() == 'die' and message.author.id == '214470441824288768':
        await client.send_message(message.channel, "As you wish master.")
        raise SystemExit

    else:
        random_chance = random.randint(0, 50) #  1 in 50 chance for the bot to add a reaction to a message.
        if random_chance == 1 and message.server:
            emoji_list = message.server.emojis
            reaction_to_message = emoji_list[random.randint(0, len(emoji_list)-1)] if len(emoji_list) else u"\U0001F44C"
            currentTime = datetime.datetime.now()
            logger.info("Adding random react to a message sent by '{0}' on server '{1}'.".format(message.author.name, message.server.name))
            try:
                await client.add_reaction(message, reaction_to_message)
            except discord.HTTPException as e:
                logger.error("There was an error when attempting to react to a message - {0}: {1}".format(type(e).__name__, e))

                
@client.event
async def on_ready(): #  Event: When the bot successfully joined the servers.
    logger.info('Logged in as {0} (ID: {1}) | {2} servers'.format(client.user.name, client.user.id, len(client.servers))) #  Print the bot's username, Discord ID and the amount of servers it's connected to.
    print('--------------')
    await client.change_presence(game=discord.Game(name='!gay <- help')) #  On Discord, this displays under the bot as "Playing !gay".
    discord.opus.load_opus(find_library('opus'))
    await refresh_server_list()


@client.event
async def on_member_join(member): #  Event: When a member joins a server the bot's connected to.
    await update_user(member)


@client.event
async def on_member_update(old, member): #  Event: When a member updates their nickname.
    await update_user(member)


@client.event
async def on_server_join(server):
    logger.info("Bot added to server: {0}. Refreshing server list.".format(server.name))
    await refresh_server_list()


@client.event
async def on_server_remove(server):
    logger.info("Bot removed from server: {0}. Refreshing server list.".format(server.name))
    await refresh_server_list()

async def main_task():
    logger.info("Starting...")
    await client.login(config["Discord"]["discord_token"])
    await client.connect()

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(main_task())
except (KeyboardInterrupt, SystemExit):
    logger.info("Logging out...")
    loop.run_until_complete(client.logout())
    print("Goodbye.")
finally:
    loop.close()
    logger.debug("Loop closed.")
