# 🤖 Telegram Ollama Bot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-Latest-blue.svg)](https://core.telegram.org/bots/api)
[![Ollama](https://img.shields.io/badge/Ollama-Compatible-green.svg)](https://ollama.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Telegram bot that brings the capabilities of local Large Language Models (LLMs) to your chats using Ollama. Chat naturally with AI models running on your own infrastructure!

## ✨ Features

- 🧠 **Multiple AI Models** - Switch between different Ollama models on the fly
- 🌍 **Multi-language Support** - Interface available in 6 languages (English, Italiano, Español, Français, Українська, Deutsch)
- 💭 **Conversational Memory** - Remembers context for natural conversations
- 👤 **Per-User Settings** - Each user can have their own model and language preferences
- 📊 **Smart Response Handling** - Automatically splits long messages or sends them as files
- 🎯 **Optimized for Telegram** - Concise responses perfect for mobile messaging
- 🔒 **Privacy-First** - Everything runs locally on your infrastructure

## 📋 Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Commands](#commands)
- [Supported Languages](#supported-languages)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🔧 Requirements

- Python 3.8 or higher
- [Ollama](https://ollama.ai/) installed and running
- A Telegram Bot Token (get one from [@BotFather](https://t.me/botfather))
- At least one Ollama model downloaded (e.g., `ollama pull llama3.1`)

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/TelegramOllamaBot.git
   cd TelegramOllamaBot
