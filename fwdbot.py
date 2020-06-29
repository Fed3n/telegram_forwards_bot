'''
Hi this is terrible code right now please understand.
Gonna be writing some documentation and cleaning things up someday.
Substitute appropriate fields to host your own forwarding bot :)
'''

import telegram
import logging
import re
import hashlib
import datetime
from telegram.ext import *

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
my_persistence = PicklePersistence(filename="data")

#Substitute with your ids and tokens
ADMINS = [ADMINS, ID, LIST]
TARGET_CH = CHANNEL_ID
BOT_TOKEN = YOUR_BOT_TOKEN

INSERT_KEY, FWD_MSG = range(2)

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

def forward(update, context):
        if update.message.chat.type == "private":
            update.message.reply_text("Enter a key of alphabetical characters for your forward. Key is not case sensitive.")
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
            if digestmsg(msg.forward_from.id, msg.forward_date, msg.text) not in context.bot_data["hash"]:
                chmsg1 = context.bot.send_message(chat_id=TARGET_CH, text=f"Key: <{key}>")
                chmsg2 = context.bot.forward_message(chat_id=TARGET_CH, from_chat_id=msg.chat.id, message_id=msg.message_id)
                context.bot_data["data"][key] = [msg, chmsg1, chmsg2]
                context.bot_data["hash"].add(digestmsg(msg.forward_from.id, msg.forward_date, msg.text))
                update.message.reply_text(f"Message saved with tag <{key}>.")
                return ConversationHandler.END
            else:
                update.message.reply_text("The message you are forwarding is already in! Aborting...")
                return ConversationHandler.END
        else:
            update.message.reply_text("Key not available anymore, please try another one.")
            return INSERT_KEY

def getter(update, context):
        for arg in context.args:
            if arg in context.bot_data["data"]:
                msg = context.bot_data["data"][arg][0]
                context.bot.forward_message(chat_id=update.message.chat.id, from_chat_id=msg.chat.id, message_id=msg.message_id)

def list_keys(update, context):
        if update.message.chat.type == "private":
            s = "Current key list:\n"
            for key, val in context.bot_data["data"].items():
                s += key + " : " + val[0].text + "\n"
            update.message.reply_text(s)

def cancel(update, context):
        update.message.reply_text("Interrupting operation.")
        return ConversationHandler.END

def remove_keys(update, context):
    if update.message.chat.type == "private" and update.message.from_user.id in ADMINS:
            update.message.reply_text("Deleting keys and corresponding messages...")
            for arg in context.args:
                if arg in context.bot_data["data"]:
                    msgs = context.bot_data["data"][arg]
                    context.bot.edit_message_text("<removed>", chat_id=TARGET_CH, message_id=msgs[1].message_id)
                    del context.bot_data["data"][arg]
                    context.bot_data["hash"].remove(digestmsg(msgs[0].forward_from.id, msgs[0].forward_date, msgs[0].text))


def error_format(update, context):
        update.message.reply_text("Please make sure your key is only alphabetical with no whitespaces.")
        return INSERT_KEY

def error(update, context):
        logger.warning(f"Update {update} caused error {context.error}")

def digestmsg(userid, date, text):
        return hashlib.sha1((str(userid)+date.strftime("%Y-%m-%d %H:%M:%S")+text).encode()).hexdigest()

def main():
        updater = Updater(BOT_TOKEN, persistence=my_persistence, use_context=True)
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help))
        dp.add_handler(CommandHandler("fwd", getter))
        dp.add_handler(CommandHandler("list", list_keys))
        dp.add_handler(CommandHandler("rmkey", remove_keys))

        conv_handler = ConversationHandler(
                entry_points=[CommandHandler("forward", forward, Filters.private)],

                states={
                    INSERT_KEY: [MessageHandler(Filters.regex(r"^[a-zA-Z]+$"), check_key),
                                 MessageHandler(~ Filters.command, error_format)],

                    FWD_MSG: [MessageHandler(Filters.forwarded, update_dict)],
                },

                fallbacks=[CommandHandler("cancel", cancel)]
        )
        
        dp.add_handler(conv_handler)
        dp.add_error_handler(error)
        
        #bot_data[data] is the key-fwd dictionary, bot_data[ids] is a fwd msg IDs set
        dp.bot_data.setdefault("data", {})
        dp.bot_data.setdefault("hash", set())

        #Start!
        updater.start_polling()
        updater.idle()

if __name__ == '__main__':
        main()
