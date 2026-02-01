# TelegramOllamaBot
A telegram bot written in python that can respond to you using a local llm from ollama.
How to set up:
Put your telegram bot token in the 12th row in the telegram_ollama_bot.py file in <PLACE_TELEGRAM_TOKEN_HERE>
Put your Ollama base URL in the 13th row in the telegram_ollama_bot.py file in <PLACE_OLLAMA_BASE_URL_HERE>
Put the default ollama model in the 14th row in the telegram_ollama_bot.py file in <PLACE_DEFAULT_MODEL_HERE>
Avaiable commands:
/reset                Wipes the context
/context              Shows the context usage (max 10 messages)
/list                 Lists all ollama models
/model <model>        Change model
/language             Lists avaiable languages
/language <language>  Change language (example: /language en, /language it ...)
/config               Shows complete configuration of the bot

Available languages:
   en - English
   it - Italiano
   es - Español
   fr - Français
   uk - Українська
   de - Deutsch

How to use: before running the bot, install the requirements in the "requirements.txt" file using "pip install -r requirements.txt" (you need to be in the right operating folder)
