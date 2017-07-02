import discord, asyncio, praw, random, logging, configparser
import defusedxml.ElementTree as defusedetree
import xml.etree.ElementTree as etree
from html import escape
from time import gmtime, strftime, time
from datetime import datetime, timedelta

# ##################### #
#                       #
# Setting up debugging. #
#                       #
# ##################### #

debugMode = True
if debugMode:
    logging.basicConfig(level=logging.INFO) # Setup logging to the console.

def debug(debugMsg):
    if debugMode:
        print("[Debug] " + debugMsg)

# ######################################################################################## #
#                                                                                          #
# Initial commands to setup things such as logging, Reddit praw, discord and the XML file. #
#                                                                                          #
# ######################################################################################## #

config = configparser.ConfigParser()
config.read("rule34_bot.cfg")

waitingToSend = False # Making a global boolean to be used in send_random_message and choose_random_message.
xmlfile = config["Data_Logging"]["xml_file"] # The location of the XML file to log data to.
logfile = config["Data_Logging"]["log_file"] # The location of the log file (becoming increasingly irrelevant).
reddit = praw.Reddit(client_id=config["Reddit"]["client_id"],client_secret=config["Reddit"]["client_secret"],user_agent=config["Reddit"]["user_agent"]) # Initalising Reddit praw.
client = discord.Client() # Creating the Discord Client object (the bot)
tree = defusedetree.parse(xmlfile) # Parsing the XML into a variable
root = tree.getroot() # Parsing the root of the XML into a variable.

# ###################################################### #
#                                                        #
# Check if the log file exists. If it doesn't, make one. #
#                                                        #
# ###################################################### #

try:
    f = open(logfile,"r")
except IOError:
    f = open(logfile,"w")
finally:
    f.close()

# ############################################################ #
#                                                              #
# Sending a random message after a user has entered a command. #
#                                                              #
# ############################################################ #

@asyncio.coroutine
def send_random_message(channel): # This function is triggered whenever someone uses the command !reddit or !rule34.
    global waitingToSend
    if not waitingToSend: # However, if the function has already been run within the past 30 minutes (or less), it will not run again.
        waitingToSend = True
        currentTime = datetime.now()
        nextHalfHour = random.randrange(30) + 1 # Choose a random number between 1 and 30
        plannedTime = currentTime + timedelta(minutes=nextHalfHour) # Get the date to print to the console.
        print("[+] Job 'choose_random_message' set to execute at " + plannedTime.strftime('%d/%m/%Y %H:%M:%S') + " (in " + str(nextHalfHour) + " minutes).")
        yield from asyncio.sleep(nextHalfHour*60) # Wait for the amount of minutes in nextHalfHour
        yield from choose_random_message(channel) # Execute choose_random_message

@asyncio.coroutine
def choose_random_message(channel):
    global waitingToSend
    waitingToSend = False # Make it so send_random_message can be executed again.
    x = random.randrange(5) # Choose a number between 0 and the number before the number in the brackets.
    print("[+] Time has been reached. Sending message ID: " + str(x))
    if x == 0: # Just say "I love the water"
        yield from client.send_message(channel, "I love the water.")
    elif x == 1: # Choose a random person in the server and say you hate them.
        i = 0
        randomUserInServer = random.randrange(channel.server.member_count)
        for y in channel.server.members:
            if i == randomUserInServer:
                yield from client.send_message(channel, "I don't like " + y.mention + " anymore. Please, just fuck off would you?")
                break
            else:
                i += 1
    elif x == 2: # Make the bot perform !r34 to itself.
        yield from client.send_message(channel, "!r34")
        post = reddit.subreddit('rule34').random()
        yield from asyncio.sleep(0.6)
        add_count(client.user, "rule34", True)
        yield from client.send_message(channel, post.url)
    elif x == 3: # Make the bot perform !reddit using a random subreddit.
        randomSub = reddit.random_subreddit(nsfw=True)
        print("[+] Retrieving a random NSFW subreddit: " + randomSub.display_name)
        yield from client.send_message(channel, "!reddit " + randomSub.display_name)
        post = randomSub.random()
        yield from asyncio.sleep(0.6)
        add_count(client.user, randomSub.display_name, True)
        yield from client.send_message(channel, post.url)
    elif x == 4:
        post = reddit.subreddit('subredditsimulator').random()
        print("[+] Got post from /r/subredditsimulator: https://www.reddit.com" + post.permalink)
        yield from client.send_message(channel, post.title)

# ################################ #
#                                  #
# Working with MySQL (logging data). #
#                                  #
# ################################ #

def mysql_update_user(usrObj):
    pass

def mysql_add_count(usrObj, subName, subExists):
    pass

def mysql_check_element_exists(userID, subName):
    pass

# ################################ #
#                                  #
# Working with XML (logging data). #
#                                  #
# ################################ #

def update_user(usrObj): # When a user joins or updates their name, update their name in the XML file. If they don't exist, make an element for them.
    for user in root.findall('user'):
        if user.attrib["id"] == str(usrObj.id):
            user.attrib["name"] = escape(usrObj.name)
            tree.write(xmlfile)
            return
    newUser = etree.SubElement(root, "user", {"name": escape(usrObj.name), "id": usrObj.id, "dateAdded": str(int(time())), "lastUsed": str(int(time()))}) # if a user doesn't exist, add them to the file
    tree.write(xmlfile) # Write to the XML file.

def add_count(usrObj, subName, subExists): # Increase the value of a sub for a user.
    subName = escape(subName) # Escape the subreddit's name.
    for user in root.findall('user'):
        if user.attrib["id"] == str(usrObj.id):
            currentTime = str(int(time()))
            user.attrib["lastUsed"] = currentTime # Make the lastUsed attribute the current time in epoch.
            if check_element_exists(usrObj.id, subName):
                for sub in user:
                    if sub.attrib["name"] == subName:
                        sub.attrib["val"] = str(int(sub.attrib["val"]) + 1) # Increase the value of the sub by one.
                        sub.attrib["last"] = currentTime
                        tree.write(xmlfile)
                        return
            else:
                subType = "sub" if subExists else "failedSub" # If the sub exists, make the element a sub, if it doesn't, make it a failedSub
                newSub = etree.SubElement(user, subType, {"name": subName, "last": currentTime, "val": "1"})
                tree.write(xmlfile)
                return

def check_element_exists(userID, subName): # Check if a sub has already been used by the user.
    for user in root.findall('user'): 
        if user.attrib["id"] == str(userID): # If the user is equal to the author,
            for sub in user: # loop through subs.
                if sub.attrib["name"] == subName:
                    return True
    return False # If the loop didn't return True, return False.

# #################################### #
#                                      #
# Displaying the XML data to the user. #
#                                      #
# #################################### #

@asyncio.coroutine
def findUserTop10Subs(channel, nameToFind): # Read the XML file and get the subs of the user.
    usersFound = [] # Make the array to contain all the users matching the search term.
    for user in root.findall('user'):
        if nameToFind.lower() in user.attrib["name"].lower():
            usersFound.append(user) # If the search term is in the users name, add them to the usersFound array.
    if len(usersFound) == 0: # If the array is empty, no users matched the search terms.
        print("[-] No users found.")
        yield from client.send_message(channel, "```No users found.```") # Inform the user.
    elif len(usersFound) == 1: # If one user was found, find their top 10 subs.
        top10Subs = [] # Make the array to contain all the subs that were found in the users element.
        for sub in usersFound[0]:
            top10Subs.append(sub) # Add all the subs to the array.
        top10Subs.sort(key=lambda x: int(x.attrib["val"]), reverse=True) # Sort the subs by the amount of times they were used by the user, with the most used being at top10Subs[0].
        subLeaderboardMsg = "" # A string that will contain the names and the values of the top 10 items in the array.
        if len(top10Subs) > 0: # If the array is bigger than 0, then add the subs to the string.
            for sub in top10Subs[:10]: # Loop through only the first 10 items in the array.
                subLeaderboardMsg += sub.attrib["name"] + " - " + sub.attrib["val"] + "\n"
        else: # If no items are in the array, the user has not used the bot.
            subLeaderboardMsg = "No data found for this user.\n" # Inform the user.
        print("[+] Retrieved stats of user '" + usersFound[0].attrib["name"] + "'.")
        yield from client.send_message(channel, "User '" + usersFound[0].attrib["name"] + "':\n```" + subLeaderboardMsg + "```") # Show the user the top 10 subs of the name they requested.
    else: # If multiple users were found, inform the user.
        userNamesFound = "" # A string that will contain all the names of the users that matched the search terms.
        for user in usersFound:
            userNamesFound += user.attrib["name"] + "\n"
        print("[-] Multiple users found.")
        yield from client.send_message(channel, "Multiple users found: ```\n" + userNamesFound + "```")

@asyncio.coroutine
def getTopThreeUsers(channel):
    pass

# ######################### #
#                           #
# Main Discord interaction. #
#                           #
# ######################### #

@client.event
@asyncio.coroutine
def on_message(message): # Event: When the bot sees a message in a channel.
    if message.author == client.user: # Making sure the bot does not reply to itself.
        return

    if message.content.lower().startswith('!rule34') or message.content.lower().startswith('!r34'):
        sub = reddit.subreddit('rule34')
        post = sub.random() # Get a random post from the sub /r/rule34.
        print("[+] '" + message.author.name + "' asked for a random post on '/r/rule34': " + post.url)
        with open(logfile,"a") as f: # Log this event to a file.
            f.write("["+strftime("%Y-%m-%d %H:%M:%S", gmtime())+"] '" + message.author.name + "' asked for a random post on '/r/rule34': " + post.url + "\n")
        add_count(message.author, "rule34", True) # Add 1 to this subreddit value under this user in the XML file.
        yield from client.send_message(message.channel, post.url)
        yield from send_random_message(message.channel) # Activate the send_random_message function.

    elif message.content.lower().startswith('!reddit '):
        subToCheck = message.content.split(' ')[1].lower()
        if len(subToCheck) > 20: # Subreddit names are a max 20 characters in length, so no point searching for one with a longer name.
            yield from client.send_message(message.channel, "That name is too long for a subreddit. Please try a shorter name.")
            yield from send_random_message(message.channel)
            return
        try:
            post = reddit.subreddit(subToCheck).random() # Get a random post from the sub /r/rule34.
            print("[+] '" + message.author.name + "' asked for a random post on '/r/" + subToCheck + "': " + post.url)
            with open(logfile,"a") as f: # Log this event to a file.
                f.write("["+strftime("%Y-%m-%d %H:%M:%S", gmtime())+"] '" + message.author.name + "' asked for a random post on '/r/" + subToCheck + "': " + post.url + "\n")
            add_count(message.author, subToCheck, True) # Add 1 to this subreddit value under this user in the XML file.
            yield from client.send_message(message.channel, post.url)
        except Exception as e: # If the sub doesn't exist (or another error occurs), tell the user.
            add_count(message.author, subToCheck, False)
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            yield from client.send_message(message.channel, fmt.format(type(e).__name__, e))
        yield from send_random_message(message.channel) # Activate the send_random_message function.

    elif message.content.lower().startswith('!stats'):
        msgArgs = message.content.split(' ')
        msgArgs.pop(0) # Remove !stats from the array of args.
        nameToFind = escape(" ".join(msgArgs)) # Convert the name to one with HTML escape codes.
        if len(msgArgs) > 0: # If the user inputted a name, search for it.
            print("[+] '" + message.author.name + "' searched for the stats of '" + nameToFind + "'.")
            yield from findUserTop10Subs(message.channel, nameToFind)
        else: # Else, get the top three users of !r34.
            yield from getTopThreeUsers(message.channel)

    elif message.content.lower().startswith('!gay'):
        print("[+] '" + message.author.name + "' asked for help.")
        yield from client.send_message(message.channel, "```\nCommands -\n\n!r34 / !rule34 - a shortcut for '!reddit rule34'. Also the main feature of this bot.\n!reddit <sub> - Sends a random post from a subreddit to the channel.\n!stats <user> - Shows the statistics for that user.\n!stats - Shows the top three users to use !r34.\n!gay - Access this help.\n\nPlaying !gay reference: https://youtu.be/hUdp1QEcxiY?t=1m40s" + "\n```")

@client.event
@asyncio.coroutine 
def on_ready(): # Event: When the bot successfully joined the servers.
    print('Logged in as '+client.user.name+' (ID: '+client.user.id+') | '+str(len(client.servers))+' servers') # Print the bot's username, Discord ID and the amount of servers it's connected to.
    print('--------------')
    yield from client.change_presence(game=discord.Game(name='!gay')) # On Discord, this displays under the bot as "Playing !gay".

@client.event
@asyncio.coroutine
def on_member_join(member): # Event: When a member joins a server the bot's connected to.
    update_user(member)

@client.event
@asyncio.coroutine
def on_member_update(old, member): # Event: When a member updates their nickname.
    update_user(member)

print("Starting...") # Start up the bot.
client.run(config["Discord"]["discord_token"])
