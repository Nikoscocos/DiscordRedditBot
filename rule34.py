import discord, asyncio, praw, random, logging
import xml.etree.ElementTree as etree
from html import escape
from time import gmtime, strftime, time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
waitingToSend = False
xmlfile = "/var/www/html/botdata.xml"
r = praw.Reddit(client_id="your client id",client_secret="your client secret",user_agent="your user agent")
client = discord.Client()
tree = etree.parse(xmlfile)
root = tree.getroot()

try:
    f = open("/var/log/discordBots/redditBot.log","r")
    f.close()
except IOError:
    f = open("/var/log/discordBots/redditBot.log","w")

@asyncio.coroutine
def send_random_message(chnl):
    global waitingToSend
    if not waitingToSend:  #TODO: Remove scheduler and add asyncio.sleep instead
        currentTime = datetime.now()
        nextHalfHour = random.randrange(30) + 1
        plannedTime = currentTime + timedelta(minutes=nextHalfHour)
        waitingToSend = True
        print("[+] Job 'choose_random_message' set to execute at " + plannedTime.strftime('%d/%m/%Y %H:%M:%S') + " (in " + str(nextHalfHour) + " minutes).")
        yield from asyncio.sleep(nextHalfHour*60)
        yield from choose_random_message(chnl)

@asyncio.coroutine
def choose_random_message(channel):
    global waitingToSend
    waitingToSend = False
    x = random.randrange(1)
    print("[+] Time has been reached. Sending message ID: " + str(x))
    print(channel.name, channel.server.name)
    if x == 0:
        yield from client.send_message(channel, "I love the water.")

def update_user(usrObj):
    for user in root.findall('user'):
        if user.attrib["id"] == str(usrObj.id):
            user.attrib["name"] = escape(usrObj.name)
            tree.write(xmlfile)
            return
    newUser = etree.SubElement(root, "user", {"name": escape(usrObj.name), "id": usrObj.id, "dateAdded": str(int(time())), "lastUsed": str(int(time()))}) # if a user doesn't exist, add them to the file
    tree.write(xmlfile)

def add_count(usrObj, subName, subExists):
    subName = escape(subName)
    for user in root.findall('user'):
        if user.attrib["id"] == str(usrObj.id):
            currentTime = str(int(time()))
            user.attrib["lastUsed"] = currentTime
            if check_element_exists(usrObj.id, subName):
                for sub in user:
                    if sub.attrib["name"] == subName:
                        sub.attrib["val"] = str(int(sub.attrib["val"]) + 1)
                        sub.attrib["last"] = currentTime
                        tree.write(xmlfile)
                        return
            else:
                subType = "sub" if subExists else "failedSub"
                newSub = etree.SubElement(user, subType, {"name": subName, "last": currentTime, "val": "1"})
                tree.write(xmlfile)
                return

def check_element_exists(userID, subName):
    for user in root.findall('user'):
        if user.attrib["id"] == str(userID):
            for sub in user:
                if sub.attrib["name"] == subName:
                    return True
    return False

@client.event
@asyncio.coroutine 
def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!rule34') or message.content.startswith('!r34'):
        #msg = 'Hello {0.author.mention}'.format(message)
        #yield from client.send_message(message.channel, msg)
        sub = r.subreddit('rule34')
        post = sub.random()
        print("[+] '" + message.author.name + "' asked for a random post on '/r/rule34': " + post.url)
        with open("/var/log/discordBots/redditBot.log","a") as f:
            f.write("["+strftime("%Y-%m-%d %H:%M:%S", gmtime())+"] '" + message.author.name + "' asked for a random post on '/r/rule34': " + post.url + "\n")
        add_count(message.author, "rule34", True)
        yield from client.send_message(message.channel, post.url)

    elif message.content.startswith('!reddit '):
        subToCheck = message.content.split(' ')[1].lower()
        try:
            post = r.subreddit(subToCheck).random()
            print("[+] '" + message.author.name + "' asked for a random post on '/r/" + subToCheck + "': " + post.url)
            with open("/var/log/discordBots/redditBot.log","a") as f:
                f.write("["+strftime("%Y-%m-%d %H:%M:%S", gmtime())+"] '" + message.author.name + "' asked for a random post on '/r/" + subToCheck + "': " + post.url + "\n")
            add_count(message.author, subToCheck, True)
            yield from client.send_message(message.channel, post.url)
        except Exception as e:
            add_count(message.author, subToCheck, False)
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            yield from client.send_message(message.channel, fmt.format(type(e).__name__, e))
        yield from send_random_message(message.channel)


    #elif message.content.startswith('!'):
    #    yield from client.send_message(message.channel, "Are you trying to bait me you fucking faggot? Do that again and you will truly burn in hell.")

@client.event
@asyncio.coroutine 
def on_ready():
    print('Logged in as ' + client.user.name)
    print('--------------')
    yield from client.change_presence(game=discord.Game(name='Gay'))

@client.event
@asyncio.coroutine
def on_member_join(member):
    update_user(member)

@client.event
@asyncio.coroutine
def on_member_update(old, member):
    update_user(member)

client.run('your discords bot token')
