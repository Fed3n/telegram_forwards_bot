import telegram
import logging
import re
import hashlib
import datetime
import os
import sys
import random
from fwd_data import *
from dotenv import load_dotenv
from telegram.ext import *

load_dotenv()

#Error checking in console
logging.basicConfig(filename="fwdbot.log", format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

#Database file for a persistent dictionary
my_persistence = PicklePersistence(filename="data")

#Using .env file, ADMINS_ID_LIST is split by ","
#But you can also not use dotenv and put information right here
ADMINS = list(map(int, os.getenv("ADMINS_ID_LIST").split(",")))
#Same for the ban list
BANS = list(map(int, os.getenv("ADMINS_ID_LIST").split(",")))
TARGET_CH = int(os.getenv("CHANNEL_ID"))
BOT = os.getenv("BOT_TOKEN")

#Limit of messages sent at once when forwarding
MSG_LIMIT = 20

#Conversation returns
INSERT_KEY, FWD_MSG = range(2)


###GENERAL COMMANDS#####
#Bot generic helper commands

def start(update, context):
    if update.message.chat.type == "private":
        update.message.reply_text("Hello this is forward bot! Type /help to learn more about me.")

def help(update, context):
    if update.message.chat.type == "private": 
        update.message.reply_text("Type /forward to begin.\n"\
                                "You will be asked to insert a key to associate to a message to memorize.\n"\
                                "Then you can get the bot to forward it again for you by issuing /fwd <key> wherever it is present."\
                                "List of keys/messages can be found in either the bot's channel in its profile or by /list.\n"\
                                "If the bot seems stuck try /cancel to abort current operation.")

########################


###INSERTION FORM#######
#Bot conversation to add a new key-value to database, issuable by all users

def forward(update, context):
    if update.message.chat.type == "private":
        update.message.reply_text("Enter a key of alphabetical characters eventually"\
                                "ending with digits for your forward. Key is not case sensitive.\n"
                                "Ex: mark, mark12")
        return INSERT_KEY
    else:
        return ConversationHandler.END

def check_key(update, context):
    update.message.reply_text("Checking for key availability...")
    key = update.message.text.lower()
    if key in context.bot_data["data"]:
        update.message.reply_text("Key is not available, please try another one.")
        return INSERT_KEY
    else:
        context.user_data["key"] = key
        update.message.reply_text("Forward message to save.")
        return FWD_MSG

def update_dict(update, context):
    msg = update.message
    key = context.user_data["key"]
    del context.user_data["key"]
    if key not in context.bot_data["data"]:
        if digestmsg(msg) not in context.bot_data["hash"]:
            chmsg1 = context.bot.send_message(chat_id=TARGET_CH, text=f"Key: <{key}>")
            chmsg2 = context.bot.forward_message(chat_id=TARGET_CH, from_chat_id=msg.chat.id, message_id=msg.message_id)
            fwd_data = fwdData(msg, chmsg1, chmsg2)
            context.bot_data["data"][key] = fwd_data
            context.bot_data["hash"].add(digestmsg(msg))
            update.message.reply_text(f"Message saved with tag <{key}>.")
            logger.info(f"User {update.message.from_user} added new message with key <{key}>.")
            return ConversationHandler.END
        else:
            update.message.reply_text("The message you are forwarding is already in! Aborting...")
            return ConversationHandler.END
    else:
        update.message.reply_text("Key not available anymore, please try another one.")
        return INSERT_KEY

def cancel(update, context):
    update.message.reply_text("Interrupting operation.")
    return ConversationHandler.END

def error_format(update, context):
    update.message.reply_text("Please make sure your key respects the format with no whitespaces.")
    return INSERT_KEY

########################


###USER COMMANDS########
#Bot commands issuable by all users, should be always safe to use

def getter(update, context):
    if len(context.args) < 1:
        update.message.reply_text("Usage: < /fwd key >, pm me to learn more!")
        return
    for arg in context.args[:MSG_LIMIT]:
        arg = arg.lower()
        if arg in context.bot_data["data"]:
            fwd_data = context.bot_data["data"][arg]
            fwd_data.counter_update()
            context.bot.forward_message(chat_id=update.message.chat.id, from_chat_id=fwd_data.fwdmsg.chat.id,
                                        message_id=fwd_data.fwdmsg.message_id)

#Very experimental tbh
def regex_getter(update, context):
    if len(context.args) < 1:
        update.message.reply_text("Usage: < /refwd regex >, pm me to learn more!")
        return
    #Get only first argument when using regex
    r = re.compile(context.args[0].lower())
    #Users can pass arbitrary expressions and those may raise exceptions
    try:
        for key in list(filter(r.match, context.bot_data["data"]))[:MSG_LIMIT]:
            fwd_data = context.bot_data["data"][key]
            fwd_data.counter_update()
            context.bot.forward_message(chat_id=update.message.chat.id, from_chat_id=fwd_data.fwdmsg.chat.id,
                                        message_id=fwd_data.fwdmsg.message_id)
    except:
        return

def rng_getter(update, context):
    fwd_data = random.choice(list(context.bot_data["data"].values()))
    fwd_data.tot_counter_update()
    context.bot.forward_message(chat_id=update.message.chat.id, from_chat_id=fwd_data.fwdmsg.chat.id,
                                message_id=fwd_data.fwdmsg.message_id)

def list_keys(update, context):
    if update.message.chat.type == "private":
        #Telegram has a max msg size, list might be
        #longer so a list of < max_length characters strings is used
        #and printed sequentially
        s_list = []
        i = 0
        s = f"Current key list({i+1}):\n"
        s_list.append(s)
        for key, val in context.bot_data["data"].items():
            #If it's a message we copy part of its text else we write it as <Media file>
            msg = val.fwdmsg
            value = ""
            if msg.text != None:
                #Prevents /list from showing full length messages if too long
                length = 30 if len(msg.text) >= 30 else len(msg.text)
                value = msg.text[:length]
            else:
                value = "<Media file>"
            value = key + " : " + value + "\n"
            if len(s_list[i])+len(value) > telegram.constants.MAX_MESSAGE_LENGTH:
                i += 1
                s = f"Current key list({i+1}):\n"
                s_list.append(s)
            s_list[i] += value
        for s in s_list:
            update.message.reply_text(s, disable_web_page_preview=True)

def get_stats(update, context):
    if len(context.args) >= 1:
        key = context.args[0].lower()
        if key in context.bot_data["data"]:
            update.message.reply_text(f"<{key}>:\n" + context.bot_data["data"][key].stats())
        else:
            update.message.reply_text(f"Couldn't find key <{key}>!")
    else:
        update.message.reply_text("Usage: < /stat key > to get stats about a key.")

########################


###ADMIN COMMANDS#######
#Commands issuable only by listed admins, could break the bot/database?

#Use /edkey oldkey newkey to replace a key with a new one
def edit_key(update, context):
    if update.message.chat.type == "private" and update.message.from_user.id in ADMINS:
        if len(context.args) < 2:
            update.message.reply_text("Usage: /edkey oldkey newkey")
            return
        oldkey = context.args[0]
        newkey = context.args[1]
        update.message.reply_text("Editing key and corresponding message...")
        #Checking if key to replace exists and replacing key does not exist already
        if oldkey in context.bot_data["data"]:
            if newkey not in context.bot_data["data"]:
                #Replacing key and editing key message in channel
                fwd_data = context.bot_data["data"][oldkey]
                context.bot_data["data"][newkey] = fwd_data
                context.bot.edit_message_text(f"Key: <{newkey}>", chat_id=TARGET_CH, message_id=fwd_data.chmsg1.message_id)
                del context.bot_data["data"][oldkey]
                update.message.reply_text("Done!")
            else:
                update.message.reply_text(f"New key <{context.args[1]}> is already present.")
        else:
            update.message.reply_text(f"Could not find key <{context.args[0]}>")

#Use /rmkey *args to remove a number of keys
def remove_keys(update, context):
    if update.message.chat.type == "private" and update.message.from_user.id in ADMINS:
        update.message.reply_text("Deleting keys and editing out corresponding messages...")
        for arg in context.args:
            if arg in context.bot_data["data"]:
                fwd_data = context.bot_data["data"][arg]
                #There are heavy limits to bots deleting messages so editing is preferred
                context.bot.edit_message_text("<removed>", chat_id=TARGET_CH, message_id=fwd_data.chmsg1.message_id)
                del context.bot_data["data"][arg]
                context.bot_data["hash"].remove(digestmsg(fwd_data.fwdmsg))
        update.message.reply_text("Done!")        

########################


###UTILITIES############

def error(update, context):
    logger.warning(f"Update {update} caused error {context.error}")

def digestmsg(msg):
    s1 = str(msg.forward_from if msg.forward_from != None else "")
    s2 = str(msg.forward_from_chat if msg.forward_from_chat != None else "")
    s3 = str(msg.forward_from_message_id)
    s4 = str(msg.forward_date.strftime("%Y-%m-%d %H:%M:%S"))
    return hashlib.sha1((s1+s2+s3+s4).encode()).hexdigest()

#Rehashes database, use whenever you modify your hash function (never use this if you don't understand, really)
def rehash_data(dispatcher):
    print("Beginning rehashing...")
    dispatcher.bot_data["hash"].clear()
    for key, val in dispatcher.bot_data["data"].items():
        msg = val.fwdmsg
        dispatcher.bot_data["hash"].add(digestmsg(msg))
    print("Done rehashing data. Hopefully.")


def remake_dict(dispatcher):
    print("Remaking dictionary...")
    for key, val in dispatcher.bot_data["data"].items():
        fwdmsg = dispatcher.bot_data["data"][key][0]
        chmsg1 = dispatcher.bot_data["data"][key][1]
        chmsg2 = dispatcher.bot_data["data"][key][2]
        dispatcher.bot_data["data"][key] = fwdData(fwdmsg, chmsg1, chmsg2)
        print(dispatcher.bot_data["data"][key].fwdmsg.forward_from_message_id)
    print("Done remaking dict. Hopefully.")

########################


def main():
    #Bot initialization with persistent data
    updater = Updater(BOT, persistence=my_persistence, use_context=True)
    dp = updater.dispatcher
        
     #Adding all possible commands to the handler
    dp.add_handler(CommandHandler("start", start, run_async=True))
    dp.add_handler(CommandHandler("help", help, run_async=True))
    dp.add_handler(CommandHandler("fwd", getter, run_async=True))
    dp.add_handler(CommandHandler("refwd", regex_getter, run_async=True))
    dp.add_handler(CommandHandler("rng", rng_getter, run_async=True))
    dp.add_handler(CommandHandler("list", list_keys, run_async=True))
    dp.add_handler(CommandHandler("stat", get_stats, run_async=True))
    dp.add_handler(CommandHandler("rmkey", remove_keys))
    dp.add_handler(CommandHandler("edkey", edit_key))
    dp.add_handler(CommandHandler("rehash", rehash_data))

    conv_handler = ConversationHandler(
            entry_points=[CommandHandler("forward", forward, Filters.chat_type.private)],

            states={
                INSERT_KEY: [MessageHandler(Filters.regex(r"^[a-zA-Z]+\d*$"), check_key),
                            MessageHandler(~ Filters.command, error_format)],

                 FWD_MSG: [MessageHandler(Filters.forwarded, update_dict)],
            },

            fallbacks=[CommandHandler("cancel", cancel)]
    )
        
    dp.add_handler(conv_handler)
    dp.add_error_handler(error)

    #Initializing bot database if first time running
    #bot_data["data"] is the key-fwd dictionary, bot_data["hash"] is a fwd msg IDs set
    dp.bot_data.setdefault("data", {})
    dp.bot_data.setdefault("hash", set())

    if len(sys.argv) > 1:
        if sys.argv[1] == "rehash":
            rehash_data(dp)
        if sys.argv[1] == "remake":
            remake_dict(dp)
        else:
            print("Invalid argument.")

    #Start! Bot will try to close nicely with CTRL+C by having issued idle()
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
     main()
