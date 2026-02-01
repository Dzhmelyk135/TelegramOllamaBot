import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import json
from io import BytesIO
from collections import defaultdict
import re

# Config
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '<PLACE_TELEGRAM_TOKEN_HERE>')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', '<PLACE_OLLAMA_BASE_URL_HERE>')  # Example: 'http://localhost:11434'
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', '<PLACE_DEFAULT_MODEL_HERE>')  # Example: 'llama3.1'

# System prompt
SYSTEM_PROMPT = """You are an AI assistant in a Telegram bot. Follow these rules:

1. Answer CONCISELY and DIRECTLY - maximum 3-4 short paragraphs
2. NO ASCII graphics, NO complex tables, NO elaborate formatting
3. Use only simple text, occasional emojis, and bullet points when needed
4. If the user asks for something long, summarize first and ask if they want more details
5. Write in the user's language, friendly but professional tone
6. DON'T say "as an AI assistant" or similar phrases - answer directly
7. If the answer would be too long, break it into key points
8. For mathematical calculations, use only simple characters, no complex formulas

Remember: you're on Telegram, not a terminal. Short, clear, readable answers."""

# Limite caratteri di Telegram
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

# Limite messaggi nel context
MAX_CONTEXT_MESSAGES = int(os.getenv('MAX_CONTEXT_MESSAGES', '10'))

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==================== TRANSLATIONS ====================
TRANSLATIONS = {
    'en': {
        'name': 'English',
        'welcome': (
            "👋 Hello! I'm a Telegram bot with Ollama.\n\n"
            "🤖 Active model: {model}\n"
            "🌐 Server: {server}\n"
            "💭 Memory: {memory} messages\n"
            "🌍 Language: {language}\n\n"
            "💡 I respond concisely and directly, perfect for Telegram!\n\n"
            "Commands:\n"
            "/start - This message\n"
            "/language - Change language\n"
            "/list - List available models\n"
            "/model <name> - Change model\n"
            "/reset - Reset conversation\n"
            "/context - Memory info\n"
            "/config - Configuration\n"
            "/help - Help\n\n"
            "💬 Write a message to chat!"
        ),
        'help': (
            "ℹ️ How to use this bot:\n\n"
            "📝 Write a message and I'll respond concisely.\n\n"
            "🤖 Model management:\n"
            "• /list - See all available models\n"
            "• /model llama3.1 - Change model\n\n"
            "💭 Conversational memory:\n"
            "The bot remembers the last {memory} messages.\n"
            "Use /reset to start over.\n\n"
            "🌍 Language:\n"
            "Use /language to change the interface language\n\n"
            "💡 Tip:\n"
            "If you want more details, ask 'explain better' or 'more details'"
        ),
        'language_list': "🌍 Available languages:\n\n{languages}\n\n💡 Use: /language <code>\nExample: /language it",
        'language_changed': "✅ Language changed to English!",
        'language_invalid': "❌ Language not available.\n\nUse /language to see available languages.",
        'language_specify': "❌ Specify the language!\n\nUsage: /language <code>\nExample: /language en\n\nUse /language without parameters to see available languages.",
        'list_loading': "🔍 Retrieving model list...",
        'list_error': "❌ Cannot retrieve models.\nVerify that Ollama is running.",
        'list_available': "🤖 Available models:\n\n{models}\n\n💡 Use: /model <name>\nExample: /model llama3.1",
        'list_active': "✅ {model} (active)\n",
        'list_inactive': "   {model}\n",
        'model_specify': "❌ Specify the model!\n\nUsage: /model <name>\nUse /list to see available models",
        'model_verifying': "🔍 Verifying model: {model}...",
        'model_not_found': "❌ Model '{model}' not found.\n\nUse /list to see available models.",
        'model_changed': "✅ Model changed!\n\nBefore: {old}\nNow: {new}\n\n🔄 Conversation reset.\nTry writing something!",
        'config': (
            "⚙️ Configuration:\n\n"
            "🤖 Active model: {model}\n"
            "🌐 Ollama server: {server}\n"
            "💭 Memory: {count}/{max} messages\n"
            "📏 Character limit: {limit}\n"
            "🎯 Response length: ~500 tokens (concise)\n"
            "🌍 Language: {language}\n\n"
            "📋 System Prompt: Active\n"
            "   Responses optimized for Telegram"
        ),
        'reset': "🔄 Conversation reset!\n\nDeleted {count} messages.\nYou can start from scratch.",
        'context_empty': "💭 Conversation memory:\n\n🤖 Model: {model}\n📊 Messages: 0\n\nStart chatting!",
        'context_info': (
            "💭 Conversation memory:\n\n"
            "🤖 Model: {model}\n"
            "📊 Messages: {count}/{max}\n"
            "📝 Total exchanges: {total}\n\n"
            "{warning}"
            "\nUse /reset to clear everything."
        ),
        'context_warning': "⚠️ Memory full! Old messages are removed.\n",
        'empty_response': "⚠️ The model did not produce a response.\nTry:\n• Change model with /list and /model\n• Rephrase the question\n• Reset conversation with /reset",
        'file_caption': "📄 The response is too long, here it is as a file.",
        'continue': "[...continues {current}/{total}]\n\n",
        'continued': "\n\n[continues...]",
        'error': "⚠️ An error occurred. Try again later."
    },
    'it': {
        'name': 'Italiano',
        'welcome': (
            "👋 Ciao! Sono un bot Telegram con Ollama.\n\n"
            "🤖 Modello attivo: {model}\n"
            "🌐 Server: {server}\n"
            "💭 Memoria: {memory} messaggi\n"
            "🌍 Lingua: {language}\n\n"
            "💡 Rispondo in modo conciso e diretto, perfetto per Telegram!\n\n"
            "Comandi:\n"
            "/start - Questo messaggio\n"
            "/language - Cambia lingua\n"
            "/list - Elenco modelli disponibili\n"
            "/model <nome> - Cambia modello\n"
            "/reset - Resetta conversazione\n"
            "/context - Info memoria\n"
            "/config - Configurazione\n"
            "/help - Aiuto\n\n"
            "💬 Scrivi un messaggio per chattare!"
        ),
        'help': (
            "ℹ️ Come usare questo bot:\n\n"
            "📝 Scrivi un messaggio e ti rispondo in modo conciso.\n\n"
            "🤖 Gestione modelli:\n"
            "• /list - Vedi tutti i modelli disponibili\n"
            "• /model llama3.1 - Cambia modello\n\n"
            "💭 Memoria conversazionale:\n"
            "Il bot ricorda gli ultimi {memory} messaggi.\n"
            "Usa /reset per ricominciare.\n\n"
            "🌍 Lingua:\n"
            "Usa /language per cambiare la lingua dell'interfaccia\n\n"
            "💡 Suggerimento:\n"
            "Se vuoi più dettagli, chiedi 'spiegami meglio' o 'più dettagli'"
        ),
        'language_list': "🌍 Lingue disponibili:\n\n{languages}\n\n💡 Usa: /language <codice>\nEsempio: /language it",
        'language_changed': "✅ Lingua cambiata in Italiano!",
        'language_invalid': "❌ Lingua non disponibile.\n\nUsa /language per vedere le lingue disponibili.",
        'language_specify': "❌ Specifica la lingua!\n\nUso: /language <codice>\nEsempio: /language it\n\nUsa /language senza parametri per vedere le lingue disponibili.",
        'list_loading': "🔍 Recupero lista modelli...",
        'list_error': "❌ Impossibile recuperare i modelli.\nVerifica che Ollama sia in esecuzione.",
        'list_available': "🤖 Modelli disponibili:\n\n{models}\n\n💡 Usa: /model <nome>\nEsempio: /model llama3.1",
        'list_active': "✅ {model} (attivo)\n",
        'list_inactive': "   {model}\n",
        'model_specify': "❌ Specifica il modello!\n\nUso: /model <nome>\nUsa /list per vedere i modelli disponibili",
        'model_verifying': "🔍 Verifico modello: {model}...",
        'model_not_found': "❌ Modello '{model}' non trovato.\n\nUsa /list per vedere i modelli disponibili.",
        'model_changed': "✅ Modello cambiato!\n\nPrima: {old}\nOra: {new}\n\n🔄 Conversazione resettata.\nProva a scrivere qualcosa!",
        'config': (
            "⚙️ Configurazione:\n\n"
            "🤖 Modello attivo: {model}\n"
            "🌐 Server Ollama: {server}\n"
            "💭 Memoria: {count}/{max} messaggi\n"
            "📏 Limite caratteri: {limit}\n"
            "🎯 Lunghezza risposta: ~500 token (concisa)\n"
            "🌍 Lingua: {language}\n\n"
            "📋 System Prompt: Attivo\n"
            "   Risposte ottimizzate per Telegram"
        ),
        'reset': "🔄 Conversazione resettata!\n\nCancellati {count} messaggi.\nPuoi ricominciare da zero.",
        'context_empty': "💭 Memoria conversazione:\n\n🤖 Modello: {model}\n📊 Messaggi: 0\n\nInizia a chattare!",
        'context_info': (
            "💭 Memoria conversazione:\n\n"
            "🤖 Modello: {model}\n"
            "📊 Messaggi: {count}/{max}\n"
            "📝 Scambi totali: {total}\n\n"
            "{warning}"
            "\nUsa /reset per cancellare tutto."
        ),
        'context_warning': "⚠️ Memoria piena! I vecchi messaggi vengono rimossi.\n",
        'empty_response': "⚠️ Il modello non ha prodotto una risposta.\nProva a:\n• Cambiare modello con /list e /model\n• Riformulare la domanda\n• Resettare la conversazione con /reset",
        'file_caption': "📄 La risposta è troppo lunga, eccola come file.",
        'continue': "[...continua {current}/{total}]\n\n",
        'continued': "\n\n[continua...]",
        'error': "⚠️ Si è verificato un errore. Riprova più tardi."
    },
    'es': {
        'name': 'Español',
        'welcome': (
            "👋 ¡Hola! Soy un bot de Telegram con Ollama.\n\n"
            "🤖 Modelo activo: {model}\n"
            "🌐 Servidor: {server}\n"
            "💭 Memoria: {memory} mensajes\n"
            "🌍 Idioma: {language}\n\n"
            "💡 ¡Respondo de forma concisa y directa, perfecto para Telegram!\n\n"
            "Comandos:\n"
            "/start - Este mensaje\n"
            "/language - Cambiar idioma\n"
            "/list - Lista de modelos disponibles\n"
            "/model <nombre> - Cambiar modelo\n"
            "/reset - Reiniciar conversación\n"
            "/context - Info de memoria\n"
            "/config - Configuración\n"
            "/help - Ayuda\n\n"
            "💬 ¡Escribe un mensaje para chatear!"
        ),
        'help': (
            "ℹ️ Cómo usar este bot:\n\n"
            "📝 Escribe un mensaje y te responderé de forma concisa.\n\n"
            "🤖 Gestión de modelos:\n"
            "• /list - Ver todos los modelos disponibles\n"
            "• /model llama3.1 - Cambiar modelo\n\n"
            "💭 Memoria conversacional:\n"
            "El bot recuerda los últimos {memory} mensajes.\n"
            "Usa /reset para empezar de nuevo.\n\n"
            "🌍 Idioma:\n"
            "Usa /language para cambiar el idioma de la interfaz\n\n"
            "💡 Consejo:\n"
            "Si quieres más detalles, pregunta 'explícalo mejor' o 'más detalles'"
        ),
        'language_list': "🌍 Idiomas disponibles:\n\n{languages}\n\n💡 Usa: /language <código>\nEjemplo: /language es",
        'language_changed': "✅ ¡Idioma cambiado a Español!",
        'language_invalid': "❌ Idioma no disponible.\n\nUsa /language para ver los idiomas disponibles.",
        'language_specify': "❌ ¡Especifica el idioma!\n\nUso: /language <código>\nEjemplo: /language es\n\nUsa /language sin parámetros para ver los idiomas disponibles.",
        'list_loading': "🔍 Recuperando lista de modelos...",
        'list_error': "❌ No se pueden recuperar los modelos.\nVerifica que Ollama esté ejecutándose.",
        'list_available': "🤖 Modelos disponibles:\n\n{models}\n\n💡 Usa: /model <nombre>\nEjemplo: /model llama3.1",
        'list_active': "✅ {model} (activo)\n",
        'list_inactive': "   {model}\n",
        'model_specify': "❌ ¡Especifica el modelo!\n\nUso: /model <nombre>\nUsa /list para ver los modelos disponibles",
        'model_verifying': "🔍 Verificando modelo: {model}...",
        'model_not_found': "❌ Modelo '{model}' no encontrado.\n\nUsa /list para ver los modelos disponibles.",
        'model_changed': "✅ ¡Modelo cambiado!\n\nAntes: {old}\nAhora: {new}\n\n🔄 Conversación reiniciada.\n¡Intenta escribir algo!",
        'config': (
            "⚙️ Configuración:\n\n"
            "🤖 Modelo activo: {model}\n"
            "🌐 Servidor Ollama: {server}\n"
            "💭 Memoria: {count}/{max} mensajes\n"
            "📏 Límite de caracteres: {limit}\n"
            "🎯 Longitud de respuesta: ~500 tokens (concisa)\n"
            "🌍 Idioma: {language}\n\n"
            "📋 System Prompt: Activo\n"
            "   Respuestas optimizadas para Telegram"
        ),
        'reset': "🔄 ¡Conversación reiniciada!\n\nEliminados {count} mensajes.\nPuedes empezar de cero.",
        'context_empty': "💭 Memoria de conversación:\n\n🤖 Modelo: {model}\n📊 Mensajes: 0\n\n¡Empieza a chatear!",
        'context_info': (
            "💭 Memoria de conversación:\n\n"
            "🤖 Modelo: {model}\n"
            "📊 Mensajes: {count}/{max}\n"
            "📝 Intercambios totales: {total}\n\n"
            "{warning}"
            "\nUsa /reset para borrar todo."
        ),
        'context_warning': "⚠️ ¡Memoria llena! Los mensajes antiguos se eliminan.\n",
        'empty_response': "⚠️ El modelo no produjo una respuesta.\nIntenta:\n• Cambiar modelo con /list y /model\n• Reformular la pregunta\n• Reiniciar la conversación con /reset",
        'file_caption': "📄 La respuesta es demasiado larga, aquí está como archivo.",
        'continue': "[...continúa {current}/{total}]\n\n",
        'continued': "\n\n[continúa...]",
        'error': "⚠️ Ocurrió un error. Inténtalo de nuevo más tarde."
    },
    'fr': {
        'name': 'Français',
        'welcome': (
            "👋 Bonjour ! Je suis un bot Telegram avec Ollama.\n\n"
            "🤖 Modèle actif : {model}\n"
            "🌐 Serveur : {server}\n"
            "💭 Mémoire : {memory} messages\n"
            "🌍 Langue : {language}\n\n"
            "💡 Je réponds de manière concise et directe, parfait pour Telegram !\n\n"
            "Commandes :\n"
            "/start - Ce message\n"
            "/language - Changer la langue\n"
            "/list - Liste des modèles disponibles\n"
            "/model <nom> - Changer de modèle\n"
            "/reset - Réinitialiser la conversation\n"
            "/context - Info mémoire\n"
            "/config - Configuration\n"
            "/help - Aide\n\n"
            "💬 Écrivez un message pour discuter !"
        ),
        'help': (
            "ℹ️ Comment utiliser ce bot :\n\n"
            "📝 Écrivez un message et je répondrai de manière concise.\n\n"
            "🤖 Gestion des modèles :\n"
            "• /list - Voir tous les modèles disponibles\n"
            "• /model llama3.1 - Changer de modèle\n\n"
            "💭 Mémoire conversationnelle :\n"
            "Le bot se souvient des {memory} derniers messages.\n"
            "Utilisez /reset pour recommencer.\n\n"
            "🌍 Langue :\n"
            "Utilisez /language pour changer la langue de l'interface\n\n"
            "💡 Conseil :\n"
            "Si vous voulez plus de détails, demandez 'expliquez mieux' ou 'plus de détails'"
        ),
        'language_list': "🌍 Langues disponibles :\n\n{languages}\n\n💡 Utilisez : /language <code>\nExemple : /language fr",
        'language_changed': "✅ Langue changée en Français !",
        'language_invalid': "❌ Langue non disponible.\n\nUtilisez /language pour voir les langues disponibles.",
        'language_specify': "❌ Spécifiez la langue !\n\nUsage : /language <code>\nExemple : /language fr\n\nUtilisez /language sans paramètres pour voir les langues disponibles.",
        'list_loading': "🔍 Récupération de la liste des modèles...",
        'list_error': "❌ Impossible de récupérer les modèles.\nVérifiez qu'Ollama est en cours d'exécution.",
        'list_available': "🤖 Modèles disponibles :\n\n{models}\n\n💡 Utilisez : /model <nom>\nExemple : /model llama3.1",
        'list_active': "✅ {model} (actif)\n",
        'list_inactive': "   {model}\n",
        'model_specify': "❌ Spécifiez le modèle !\n\nUsage : /model <nom>\nUtilisez /list pour voir les modèles disponibles",
        'model_verifying': "🔍 Vérification du modèle : {model}...",
        'model_not_found': "❌ Modèle '{model}' non trouvé.\n\nUtilisez /list pour voir les modèles disponibles.",
        'model_changed': "✅ Modèle changé !\n\nAvant : {old}\nMaintenant : {new}\n\n🔄 Conversation réinitialisée.\nEssayez d'écrire quelque chose !",
        'config': (
            "⚙️ Configuration :\n\n"
            "🤖 Modèle actif : {model}\n"
            "🌐 Serveur Ollama : {server}\n"
            "💭 Mémoire : {count}/{max} messages\n"
            "📏 Limite de caractères : {limit}\n"
            "🎯 Longueur de réponse : ~500 tokens (concise)\n"
            "🌍 Langue : {language}\n\n"
            "📋 System Prompt : Actif\n"
            "   Réponses optimisées pour Telegram"
        ),
        'reset': "🔄 Conversation réinitialisée !\n\nSupprimé {count} messages.\nVous pouvez recommencer.",
        'context_empty': "💭 Mémoire de conversation :\n\n🤖 Modèle : {model}\n📊 Messages : 0\n\nCommencez à discuter !",
        'context_info': (
            "💭 Mémoire de conversation :\n\n"
            "🤖 Modèle : {model}\n"
            "📊 Messages : {count}/{max}\n"
            "📝 Échanges totaux : {total}\n\n"
            "{warning}"
            "\nUtilisez /reset pour tout effacer."
        ),
        'context_warning': "⚠️ Mémoire pleine ! Les anciens messages sont supprimés.\n",
        'empty_response': "⚠️ Le modèle n'a pas produit de réponse.\nEssayez :\n• Changer de modèle avec /list et /model\n• Reformuler la question\n• Réinitialiser la conversation avec /reset",
        'file_caption': "📄 La réponse est trop longue, la voici en fichier.",
        'continue': "[...continue {current}/{total}]\n\n",
        'continued': "\n\n[continue...]",
        'error': "⚠️ Une erreur s'est produite. Réessayez plus tard."
    },
    'uk': {
        'name': 'Українська',
        'welcome': (
            "👋 Привіт! Я Telegram бот з Ollama.\n\n"
            "🤖 Активна модель: {model}\n"
            "🌐 Сервер: {server}\n"
            "💭 Пам'ять: {memory} повідомлень\n"
            "🌍 Мова: {language}\n\n"
            "💡 Я відповідаю стисло і прямо, ідеально для Telegram!\n\n"
            "Команди:\n"
            "/start - Це повідомлення\n"
            "/language - Змінити мову\n"
            "/list - Список доступних моделей\n"
            "/model <назва> - Змінит�� модель\n"
            "/reset - Скинути розмову\n"
            "/context - Інфо про пам'ять\n"
            "/config - Конфігурація\n"
            "/help - Допомога\n\n"
            "💬 Напишіть повідомлення, щоб почати чат!"
        ),
        'help': (
            "ℹ️ Як використовувати цей бот:\n\n"
            "📝 Напишіть повідомлення і я відповім стисло.\n\n"
            "🤖 Керування моделями:\n"
            "• /list - Переглянути всі доступні моделі\n"
            "• /model llama3.1 - Змінити модель\n\n"
            "💭 Розмовна пам'ять:\n"
            "Бот пам'ятає останні {memory} повідомлень.\n"
            "Використовуйте /reset, щоб почати спочатку.\n\n"
            "🌍 Мова:\n"
            "Використовуйте /language, щоб змінити мову інтерфейсу\n\n"
            "💡 Порада:\n"
            "Якщо потрібно більше деталей, запитайте 'поясніть краще' або 'більше деталей'"
        ),
        'language_list': "🌍 Доступні мови:\n\n{languages}\n\n💡 Використовуйте: /language <код>\nПриклад: /language uk",
        'language_changed': "✅ Мову змінено на Українську!",
        'language_invalid': "❌ Мова недоступна.\n\nВикористовуйте /language, щоб побачити доступні мови.",
        'language_specify': "❌ Вкажіть мову!\n\nВикористання: /language <код>\nПриклад: /language uk\n\nВикористовуйте /language без параметрів, щоб побачити доступні мови.",
        'list_loading': "🔍 Отримання списку моделей...",
        'list_error': "❌ Неможливо отримати моделі.\nПереконайтеся, що Ollama запущена.",
        'list_available': "🤖 Доступні моделі:\n\n{models}\n\n💡 Використовуйте: /model <назва>\nПриклад: /model llama3.1",
        'list_active': "✅ {model} (активна)\n",
        'list_inactive': "   {model}\n",
        'model_specify': "❌ Вкажіть модель!\n\nВикористання: /model <назва>\nВикористовуйте /list, щоб побачити доступні моделі",
        'model_verifying': "🔍 Перевірка моделі: {model}...",
        'model_not_found': "❌ М��дель '{model}' не знайдена.\n\nВикористовуйте /list, щоб побачити доступні моделі.",
        'model_changed': "✅ Модель змінено!\n\nДо: {old}\nТепер: {new}\n\n🔄 Розмову скинуто.\nСпробуйте щось написати!",
        'config': (
            "⚙️ Конфігурація:\n\n"
            "🤖 Активна модель: {model}\n"
            "🌐 Сервер Ollama: {server}\n"
            "💭 Пам'ять: {count}/{max} повідомлень\n"
            "📏 Ліміт символів: {limit}\n"
            "🎯 Довжина відповіді: ~500 токенів (стисла)\n"
            "🌍 Мова: {language}\n\n"
            "📋 System Prompt: Активний\n"
            "   Відповіді оптимізовані для Telegram"
        ),
        'reset': "🔄 Розмову скинуто!\n\nВидалено {count} повідомлень.\nМожете почати спочатку.",
        'context_empty': "💭 Пам'ять розмови:\n\n🤖 Модель: {model}\n📊 Повідомлення: 0\n\nПочніть чат!",
        'context_info': (
            "💭 Пам'ять розмови:\n\n"
            "🤖 Модель: {model}\n"
            "📊 Повідомлення: {count}/{max}\n"
            "📝 Всього обмінів: {total}\n\n"
            "{warning}"
            "\nВикористовуйте /reset, щоб очистити все."
        ),
        'context_warning': "⚠️ Пам'ять заповнена! Старі повідомлення видаляються.\n",
        'empty_response': "⚠️ Модель не створила відповіді.\nСпробуйте:\n• Змінити модель за допомогою /list і /model\n• Переформулювати питання\n• Скинути розмову за допомогою /reset",
        'file_caption': "📄 Відповідь занадто довга, ось вона як файл.",
        'continue': "[...продовжується {current}/{total}]\n\n",
        'continued': "\n\n[продовжується...]",
        'error': "⚠️ Сталася помилка. Спробуйте пізніше."
    },
    'de': {
        'name': 'Deutsch',
        'welcome': (
            "👋 Hallo! Ich bin ein Telegram-Bot mit Ollama.\n\n"
            "🤖 Aktives Modell: {model}\n"
            "🌐 Server: {server}\n"
            "💭 Speicher: {memory} Nachrichten\n"
            "🌍 Sprache: {language}\n\n"
            "💡 Ich antworte prägnant und direkt, perfekt für Telegram!\n\n"
            "Befehle:\n"
            "/start - Diese Nachricht\n"
            "/language - Sprache ändern\n"
            "/list - Verfügbare Modelle auflisten\n"
            "/model <name> - Modell wechseln\n"
            "/reset - Konversation zurücksetzen\n"
            "/context - Speicher-Info\n"
            "/config - Konfiguration\n"
            "/help - Hilfe\n\n"
            "💬 Schreiben Sie eine Nachricht zum Chatten!"
        ),
        'help': (
            "ℹ️ So verwenden Sie diesen Bot:\n\n"
            "📝 Schreiben Sie eine Nachricht und ich antworte prägnant.\n\n"
            "🤖 Modellverwaltung:\n"
            "• /list - Alle verfügbaren Modelle anzeigen\n"
            "• /model llama3.1 - Modell wechseln\n\n"
            "💭 Gesprächsspeicher:\n"
            "Der Bot merkt sich die letzten {memory} Nachrichten.\n"
            "Verwenden Sie /reset zum Neubeginn.\n\n"
            "🌍 Sprache:\n"
            "Verwenden Sie /language, um die Oberflächensprache zu ändern\n\n"
            "💡 Tipp:\n"
            "Wenn Sie mehr Details wollen, fragen Sie 'erkläre besser' oder 'mehr Details'"
        ),
        'language_list': "🌍 Verfügbare Sprachen:\n\n{languages}\n\n💡 Verwenden Sie: /language <code>\nBeispiel: /language de",
        'language_changed': "✅ Sprache auf Deutsch geändert!",
        'language_invalid': "❌ Sprache nicht verfügbar.\n\nVerwenden Sie /language, um verfügbare Sprachen zu sehen.",
        'language_specify': "❌ Geben Sie die Sprache an!\n\nVerwendung: /language <code>\nBeispiel: /language de\n\nVerwenden Sie /language ohne Parameter, um verfügbare Sprachen zu sehen.",
        'list_loading': "🔍 Modellliste wird abgerufen...",
        'list_error': "❌ Modelle können nicht abgerufen werden.\nÜberprüfen Sie, ob Ollama läuft.",
        'list_available': "🤖 Verfügbare Modelle:\n\n{models}\n\n💡 Verwenden Sie: /model <name>\nBeispiel: /model llama3.1",
        'list_active': "✅ {model} (aktiv)\n",
        'list_inactive': "   {model}\n",
        'model_specify': "❌ Geben Sie das Modell an!\n\nVerwendung: /model <name>\nVerwenden Sie /list, um verfügbare Modelle zu sehen",
        'model_verifying': "🔍 Überprüfe Modell: {model}...",
        'model_not_found': "❌ Modell '{model}' nicht gefunden.\n\nVerwenden Sie /list, um verfügbare Modelle zu sehen.",
        'model_changed': "✅ Modell geändert!\n\nVorher: {old}\nJetzt: {new}\n\n🔄 Konversation zurückgesetzt.\nVersuchen Sie, etwas zu schreiben!",
        'config': (
            "⚙️ Konfiguration:\n\n"
            "🤖 Aktives Modell: {model}\n"
            "🌐 Ollama-Server: {server}\n"
            "💭 Speicher: {count}/{max} Nachrichten\n"
            "📏 Zeichenlimit: {limit}\n"
            "🎯 Antwortlänge: ~500 Token (prägnant)\n"
            "🌍 Sprache: {language}\n\n"
            "📋 System Prompt: Aktiv\n"
            "   Antworten für Telegram optimiert"
        ),
        'reset': "🔄 Konversation zurückgesetzt!\n\n{count} Nachrichten gelöscht.\nSie können von vorne beginnen.",
        'context_empty': "💭 Gesprächsspeicher:\n\n🤖 Modell: {model}\n📊 Nachrichten: 0\n\nBeginnen Sie zu chatten!",
        'context_info': (
            "💭 Gesprächsspeicher:\n\n"
            "🤖 Modell: {model}\n"
            "📊 Nachrichten: {count}/{max}\n"
            "📝 Gesamte Austausche: {total}\n\n"
            "{warning}"
            "\nVerwenden Sie /reset, um alles zu löschen."
        ),
        'context_warning': "⚠️ Speicher voll! Alte Nachrichten werden entfernt.\n",
        'empty_response': "⚠️ Das Modell hat keine Antwort erzeugt.\nVersuchen Sie:\n• Modell wechseln mit /list und /model\n• Frage umformulieren\n• Konversation zurücksetzen mit /reset",
        'file_caption': "📄 Die Antwort ist zu lang, hier ist sie als Datei.",
        'continue': "[...fortgesetzt {current}/{total}]\n\n",
        'continued': "\n\n[wird fortgesetzt...]",
        'error': "⚠️ Ein Fehler ist aufgetreten. Versuchen Sie es später erneut."
    }
}


class ConversationMemory:
    """Class to manage conversation memory per user"""
    
    def __init__(self, max_messages: int = MAX_CONTEXT_MESSAGES):
        self.conversations = defaultdict(list)
        self.user_models = defaultdict(lambda: OLLAMA_MODEL)
        self.user_languages = defaultdict(lambda: 'en')  # Lingua per utente
        self.max_messages = max_messages
    
    def add_message(self, user_id: int, role: str, content: str):
        self.conversations[user_id].append({'role': role, 'content': content})
        if len(self.conversations[user_id]) > self.max_messages * 2:
            self.conversations[user_id] = self.conversations[user_id][-(self.max_messages * 2):]
    
    def get_conversation(self, user_id: int) -> list:
        return self.conversations[user_id]
    
    def clear_conversation(self, user_id: int):
        if user_id in self.conversations:
            del self.conversations[user_id]
    
    def get_message_count(self, user_id: int) -> int:
        return len([m for m in self.conversations[user_id] if m['role'] == 'user'])
    
    def set_model(self, user_id: int, model: str):
        self.user_models[user_id] = model
    
    def get_model(self, user_id: int) -> str:
        return self.user_models[user_id]
    
    def set_language(self, user_id: int, language: str):
        """Imposta la lingua per l'utente"""
        self.user_languages[user_id] = language
    
    def get_language(self, user_id: int) -> str:
        """Ottiene la lingua dell'utente"""
        return self.user_languages[user_id]


class OllamaClient:
    """Client to interact with Ollama"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    def generate(self, prompt: str, model: str, context_messages: list = None, 
                 use_system_prompt: bool = True) -> str:
        try:
            url = f"{self.base_url}/api/generate"
            full_prompt = self._build_prompt_with_context(prompt, context_messages, use_system_prompt, model)
            
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 500
                }
            }
            
            logger.info(f"Richiesta a Ollama con modello: {model}")
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            raw_response = result.get('response', '')
            logger.info(f"Risposta ricevuta: {len(raw_response)} caratteri")
            
            cleaned_response = self._clean_response(raw_response, model)
            
            if not cleaned_response or cleaned_response.strip() == '':
                logger.warning(f"Risposta vuota da modello {model}")
                return f"⚠️ Model {model} produced no valid response.\n\nTry:\n• /reset to reset conversation\n• /list to change model"
            
            return cleaned_response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore nella richiesta a Ollama: {e}")
            return f"❌ Connection error to Ollama: {str(e)}"
        except Exception as e:
            logger.error(f"Errore imprevisto: {e}", exc_info=True)
            return f"❌ Unexpected error: {str(e)}"
    
    def _clean_response(self, response: str, model: str) -> str:
        if not response:
            return ""
        
        if 'deepseek-r1' in model.lower():
            response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
            response = re.sub(r'</?think>', '', response)
        
        response = re.sub(r'\n{4,}', '\n\n', response)
        
        lines = response.split('\n')
        cleaned_lines = []
        ascii_art_count = 0
        
        for line in lines:
            special_chars = sum(1 for c in line if c in '│─├└┌┐┘┤┬┴┼═║╔╗╚╝╠╣╦╩╬')
            if special_chars > 10:
                ascii_art_count += 1
                if ascii_art_count > 3:
                    continue
            else:
                ascii_art_count = 0
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _build_prompt_with_context(self, current_prompt: str, context_messages: list = None,
                                   use_system_prompt: bool = True, model: str = "") -> str:
        prompt_parts = []
        is_deepseek_r1 = 'deepseek-r1' in model.lower()
        
        if is_deepseek_r1:
            logger.info("Usando formato prompt per DeepSeek-R1")
            if context_messages and len(context_messages) > 0:
                for msg in context_messages[-4:]:
                    if msg['role'] == 'user':
                        prompt_parts.append(f"User: {msg['content']}\n")
                    else:
                        prompt_parts.append(f"Assistant: {msg['content']}\n")
            prompt_parts.append(f"User: {current_prompt}\n")
            prompt_parts.append("Assistant:")
        else:
            logger.info(f"Usando formato prompt standard per {model}")
            if use_system_prompt:
                prompt_parts.append(f"[SYSTEM]\n{SYSTEM_PROMPT}\n[/SYSTEM]\n\n")
            if context_messages and len(context_messages) > 0:
                prompt_parts.append("Previous conversation:\n")
                for msg in context_messages:
                    if msg['role'] == 'user':
                        prompt_parts.append(f"\nUser: {msg['content']}")
                    else:
                        prompt_parts.append(f"\nAssistant: {msg['content']}")
                prompt_parts.append("\n\n")
            prompt_parts.append(f"User: {current_prompt}")
            prompt_parts.append("\nAssistant:")
        
        return "".join(prompt_parts)
    
    def list_models(self) -> list:
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        except Exception as e:
            logger.error(f"Errore nel recupero modelli: {e}")
            return []


# Inizializza
ollama_client = OllamaClient(OLLAMA_BASE_URL)
conversation_memory = ConversationMemory(MAX_CONTEXT_MESSAGES)


def get_text(user_id: int, key: str, **kwargs) -> str:
    """Get the translated text for the user"""
    lang = conversation_memory.get_language(user_id)
    if lang not in TRANSLATIONS:
        lang = 'en'
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS['en'].get(key, key))
    return text.format(**kwargs) if kwargs else text


def split_message(text: str, max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> list:
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        
        split_pos = max_length
        for delimiter, ratio in [('\n\n', 0.5), ('\n', 0.5), ('. ', 0.5), (' ', 0)]:
            pos = text[:max_length].rfind(delimiter)
            if pos > max_length * ratio:
                split_pos = pos + len(delimiter)
                break
        
        parts.append(text[:split_pos])
        text = text[split_pos:]
    
    return parts


async def send_long_message(update: Update, text: str, user_id: int):
    if not text or text.strip() == '':
        logger.error("Tentativo di inviare messaggio vuoto")
        await update.message.reply_text(get_text(user_id, 'empty_response'))
        return
    
    if len(text) > 10000:
        logger.info(f"Messaggio molto lungo ({len(text)} caratteri), invio come file")
        file_content = BytesIO(text.encode('utf-8'))
        file_content.name = 'risposta.txt'
        await update.message.reply_document(
            document=file_content,
            filename='risposta.txt',
            caption=get_text(user_id, 'file_caption')
        )
        return
    
    parts = split_message(text)
    if len(parts) > 1:
        logger.info(f"Messaggio diviso in {len(parts)} parti")
    
    for i, part in enumerate(parts):
        if i > 0:
            part = get_text(user_id, 'continue', current=i+1, total=len(parts)) + part
        elif len(parts) > 1:
            part = part + get_text(user_id, 'continued')
        await update.message.reply_text(part)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_model = conversation_memory.get_model(user_id)
    current_lang = conversation_memory.get_language(user_id)
    
    welcome = get_text(
        user_id, 'welcome',
        model=current_model,
        server=OLLAMA_BASE_URL,
        memory=MAX_CONTEXT_MESSAGES,
        language=TRANSLATIONS[current_lang]['name']
    )
    await update.message.reply_text(welcome)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    help_text = get_text(user_id, 'help', memory=MAX_CONTEXT_MESSAGES)
    await update.message.reply_text(help_text)


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        # Mostra lingue disponibili
        lang_list = []
        current_lang = conversation_memory.get_language(user_id)
        
        for code, trans in TRANSLATIONS.items():
            if code == current_lang:
                lang_list.append(f"✅ {code} - {trans['name']}")
            else:
                lang_list.append(f"   {code} - {trans['name']}")
        
        languages_text = '\n'.join(lang_list)
        await update.message.reply_text(
            get_text(user_id, 'language_list', languages=languages_text)
        )
        return
    
    new_lang = context.args[0].lower()
    
    if new_lang not in TRANSLATIONS:
        await update.message.reply_text(get_text(user_id, 'language_invalid'))
        return
    
    conversation_memory.set_language(user_id, new_lang)
    await update.message.reply_text(get_text(user_id, 'language_changed'))
    logger.info(f"User {user_id} changed language to {new_lang}")


async def list_models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, 'list_loading'))
    
    models = ollama_client.list_models()
    
    if not models:
        await update.message.reply_text(get_text(user_id, 'list_error'))
        return
    
    current_model = conversation_memory.get_model(user_id)
    models_text = ""
    
    for model in sorted(models):
        if model == current_model:
            models_text += get_text(user_id, 'list_active', model=model)
        else:
            models_text += get_text(user_id, 'list_inactive', model=model)
    
    await update.message.reply_text(
        get_text(user_id, 'list_available', models=models_text)
    )


async def set_model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(get_text(user_id, 'model_specify'))
        return
    
    new_model = ' '.join(context.args)
    await update.message.reply_text(get_text(user_id, 'model_verifying', model=new_model))
    
    available_models = ollama_client.list_models()
    
    if new_model not in available_models:
        await update.message.reply_text(get_text(user_id, 'model_not_found', model=new_model))
        return
    
    old_model = conversation_memory.get_model(user_id)
    conversation_memory.set_model(user_id, new_model)
    conversation_memory.clear_conversation(user_id)
    
    await update.message.reply_text(
        get_text(user_id, 'model_changed', old=old_model, new=new_model)
    )
    logger.info(f"User {user_id} changed model: {old_model} → {new_model}")


async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg_count = conversation_memory.get_message_count(user_id)
    current_model = conversation_memory.get_model(user_id)
    current_lang = conversation_memory.get_language(user_id)
    
    config_text = get_text(
        user_id, 'config',
        model=current_model,
        server=OLLAMA_BASE_URL,
        count=msg_count,
        max=MAX_CONTEXT_MESSAGES,
        limit=TELEGRAM_MAX_MESSAGE_LENGTH,
        language=TRANSLATIONS[current_lang]['name']
    )
    await update.message.reply_text(config_text)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg_count = conversation_memory.get_message_count(user_id)
    conversation_memory.clear_conversation(user_id)
    
    await update.message.reply_text(get_text(user_id, 'reset', count=msg_count))
    logger.info(f"Reset conversation for user {user_id}")


async def context_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg_count = conversation_memory.get_message_count(user_id)
    conversation = conversation_memory.get_conversation(user_id)
    current_model = conversation_memory.get_model(user_id)
    
    if msg_count == 0:
        await update.message.reply_text(
            get_text(user_id, 'context_empty', model=current_model)
        )
    else:
        warning = get_text(user_id, 'context_warning') if msg_count >= MAX_CONTEXT_MESSAGES else ""
        await update.message.reply_text(
            get_text(user_id, 'context_info',
                    model=current_model,
                    count=msg_count,
                    max=MAX_CONTEXT_MESSAGES,
                    total=len(conversation),
                    warning=warning)
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    
    logger.info(f"Message from {user_name} (ID: {user_id}): {user_message}")
    await update.message.chat.send_action(action="typing")
    
    current_model = conversation_memory.get_model(user_id)
    conversation_history = conversation_memory.get_conversation(user_id)
    
    response = ollama_client.generate(
        user_message, 
        current_model, 
        conversation_history,
        use_system_prompt=True
    )
    
    conversation_memory.add_message(user_id, 'user', user_message)
    conversation_memory.add_message(user_id, 'assistant', response)
    
    msg_count = conversation_memory.get_message_count(user_id)
    logger.info(f"Response: {len(response)} chars with {current_model} (context: {msg_count})")
    
    await send_long_message(update, response, user_id)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    if update and update.message:
        user_id = update.effective_user.id
        await update.message.reply_text(get_text(user_id, 'error'))


def main():
    if TELEGRAM_TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN_HERE':
        logger.error("ERROR: Set TELEGRAM_TOKEN!")
        print("\n⚠️ ERROR: Set TELEGRAM_TOKEN!")
        return
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("list", list_models_command))
    application.add_handler(CommandHandler("model", set_model_command))
    application.add_handler(CommandHandler("config", config_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("context", context_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Bot started!")
    print(f"🤖 Bot started!")
    print(f"📦 Default model: {OLLAMA_MODEL}")
    print(f"🌐 Ollama server: {OLLAMA_BASE_URL}")
    print(f"💭 Context: {MAX_CONTEXT_MESSAGES} messages")
    print(f"🌍 Languages: {len(TRANSLATIONS)}")
    print(f"🎯 System Prompt: Active (concise responses)")
    print("✅ Bot running... Press Ctrl+C to stop.\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()