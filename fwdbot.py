import telegram
import logging
import re
import hashlib
import datetime
import os
import random
from dotenv import load_dotenv
from telegram.ext import *

load_dotenv()

#Error checking in console
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

#Database file for a persistent dictionary
my_persistence = PicklePersistence(filename="data")

#Using .env file, ADMINS_ID_LIST is split by ","
#But you can also not use dotenv and put information right here
ADMINS = os.getenv("ADMINS_ID_LIST").split(",")
ADMINS = list(map(int, ADMINS))
TARGET_CH = int(os.getenv("CHANNEL_ID"))
BOT = os.getenv("BOT_TOKEN")

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
        if update.message.chat.type != "private" and update.message.from_user.id not in ADMINS:
             return
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
                context.bot_data["data"][key] = [msg, chmsg1, chmsg2]
                context.bot_data["hash"].add(digestmsg(msg))
                update.message.reply_text(f"Message saved with tag <{key}>.")
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

@run_async
def getter(update, context):
        if len(context.args) < 1:
            update.message.reply_text("Usage: < /fwd key >, pm me to learn more!")
        for arg in context.args:
            if arg in context.bot_data["data"]:
                msg = context.bot_data["data"][arg][0]
                context.bot.forward_message(chat_id=update.message.chat.id, from_chat_id=msg.chat.id, message_id=msg.message_id)

@run_async
def rng_getter(update, context):
        msg = random.choice(list(context.bot_data["data"].values()))[0]
        context.bot.forward_message(chat_id=update.message.chat.id, from_chat_id=msg.chat.id, message_id=msg.message_id)

@run_async
def list_keys(update, context):
        if update.message.chat.type == "private":
            s = "Current key list:\n"
            for key, val in context.bot_data["data"].items():
                #Prevents /list from showing full long messages
                length = 30 if len(val[0].text) >= 30 else len(val[0].text)
                s += key + " : " + val[0].text[:length] + "\n"
            update.message.reply_text(s, disable_web_page_preview=True)

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
                    msgs = context.bot_data["data"][oldkey]
                    context.bot_data["data"][newkey] = msgs
                    context.bot.edit_message_text(f"Key: <{newkey}>", chat_id=TARGET_CH, message_id=msgs[1].message_id)
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
                    msgs = context.bot_data["data"][arg]
                    #There are heavy limits to bots deleting messages so editing is preferred
                    context.bot.edit_message_text("<removed>", chat_id=TARGET_CH, message_id=msgs[1].message_id)
                    del context.bot_data["data"][arg]
                    context.bot_data["hash"].remove(digestmsg(msgs[0]))
            update.message.reply_text("Done!")

#Rehashes database, use whenever you modify your hash function (never use this if you don't understand, really)
def rehash_data(update, context):
        if update.message.chat.type == "private" and update.message.from_user.id in ADMINS:
            update.message.reply_text("Starting rehashing, DO NOT INTERRUPT OPERATION.")
            context.bot_data["hash"].clear()
            for key, val in context.bot_data["data"].items():
                msg = val[0]
                context.bot_data["hash"].add(digestmsg(msg))
            update.message.reply_text("Done rehashing data. Hopefully.")
        


########################


###UTILITIES############

def error(update, context):
        logger.warning(f"Update {update} caused error {context.error}")

def digestmsg(msg):
        return hashlib.sha1(msg.forward_date.strftime("%Y-%m-%d %H:%M:%S").encode()).hexdigest()

########################


def main():
        #Bot initialization with persistent data
        updater = Updater(BOT, persistence=my_persistence, use_context=True)
        dp = updater.dispatcher
        
        #Adding all possible commands to the handler
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help))
        dp.add_handler(CommandHandler("fwd", getter))
        dp.add_handler(CommandHandler("rng", rng_getter))
        dp.add_handler(CommandHandler("list", list_keys))
        dp.add_handler(CommandHandler("rmkey", remove_keys))
        dp.add_handler(CommandHandler("edkey", edit_key))
        dp.add_handler(CommandHandler("rehash", rehash_data))

        conv_handler = ConversationHandler(
                entry_points=[CommandHandler("forward", forward, Filters.private)],

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

        #Start! Bot will try to close nicely with CTRL+C by having issued idle()
        updater.start_polling()
        updater.idle()

if __name__ == '__main__':
        main()
