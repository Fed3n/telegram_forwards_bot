# telegram_forwarding_bot

This is a telegram bot used to manage a dictionary of forwarded messages. Users are able to send a key and a forwarded message to the bot and the pair will be saved in its internal database and then sent in a telegram channel linked to it. The users will then be able to use the bot to forward those messages in any chat where the bot is present.

## Bot Usage

The bot comes with some commands available to all users such as:
- /forward  
Begins key, message forwarding procedure (private chat only). User will be prompted to insert a key and if available then prompted to forward a message. If all goes correctly the key, message pair will be saved.
- /fwd key*  
Forward one or more messages by their keys to the chat where it is called.
- /rng  
For fun command to send a random stored message.
- /list  
Lists all current key-message pairs, but it is a bit rough, bot channel should be preferred for key-message references. Media files will be listed as <Media file>.

And with some admin-only commands to manage the database:
- /rmkey key*  
Will remove all keys listed as arguments and their values from the database, key message in bot's channel will be edited to <removed>.
- /edit oldkey newkey  
Will edit the key value of the first argument into the key value of the second argument and also edit bot's channel to reflect that.
- /rehash  
Used during development whenever I change my hash function to check for existing messages and I need to recompile the set.

## Setting up your own bot

This bot is developed in python3 using the [python-telegram-bot library](https://python-telegram-bot.readthedocs.io/en/stable/). I am using [python-dotenv](https://pypi.org/project/python-dotenv/) aswell but you can also make without.  
First of all you will need your own [telegram bot](https://core.telegram.org/bots) (and its bot token), a telegram channel (and its channel id) and your (and maybe your friends'?) user id to set as admin. You can either use dotenv like I did and put an admin integer list, a channel integer id and a bot token string in a .env file inside your directory or remove dotenv imports and os.getdotenv("") references and put your data in clear instead (which is no big deal as long as the code does not leak). When this is set up you should be already able to run your istance of the bot. The database is a very simple implementation of persistence that came with the library, with a "data" textfile in your directory, be careful not to delete it by mistake if you do not wanna clear all your dictionary.  
This bot will not save any kind of user data (exception made for forwarded messages, obviously).


## Contributing
This is a very simple for fun project so there might not be any further development, but pull requests, suggestions or issues are still very welcome. :)


## License
[MIT](https://choosealicense.com/licenses/mit/)
