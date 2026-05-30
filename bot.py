import os
import httpx
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Читаем документ при запуске
with open("document.md", "r", encoding="utf-8") as f:
    DOCUMENT = f.read()

SYSTEM_PROMPT = f"""Ты — помощник по руководству эксплуатации автомобиля Volkswagen Lavida 2022.
Отвечай ТОЛЬКО на основе документа ниже. Если ответа в документе нет — так и скажи.
Отвечай по-русски, кратко и по делу. Не используй markdown-форматирование, звёздочки, решётки и другие спецсимволы — пиши обычным текстом. Если упоминаешь названия кнопок или надписей на панелях автомобиля — дублируй их на английском в скобках, например: кнопка запуска двигателя (Start/Stop).

ДОКУМЕНТ:
{DOCUMENT}
"""

# Хранилище истории: {user_id: {"messages": [...], "last_time": timestamp}}
user_sessions = {}
SESSION_TIMEOUT = 30  # секунд


def get_history(user_id: int) -> list:
    now = time.time()
    session = user_sessions.get(user_id)
    if session and (now - session["last_time"]) < SESSION_TIMEOUT:
        return session["messages"]
    return []


def save_message(user_id: int, role: str, content: str):
    now = time.time()
    if user_id not in user_sessions:
        user_sessions[user_id] = {"messages": [], "last_time": now}
    session = user_sessions[user_id]
    # Если прошло больше 60 секунд — сбрасываем историю
    if (now - session["last_time"]) >= SESSION_TIMEOUT:
        session["messages"] = []
    session["messages"].append({"role": role, "content": content})
    session["last_time"] = now
    # Храним не более 10 сообщений
    if len(session["messages"]) > 10:
        session["messages"] = session["messages"][-10:]


async def ask_ai(user_id: int, question: str) -> str:
    history = get_history(user_id)
    messages = history + [{"role": "user", "content": question}]

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com",
            },
            json={
                "model": "openrouter/auto",
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            },
        )
        data = response.json()
        if "choices" not in data:
            return f"Ошибка API: {data.get('error', {}).get('message', str(data))}"
        return data["choices"][0]["message"]["content"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу найти информацию по руководству VW Lavida 2022.\n\n"
        "Задайте любой вопрос, например:\n"
        "Что означает красная лампа масла?\n"
        "Как включить задний противотуманный фонарь?\n"
        "Как отрегулировать сиденье?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    question = update.message.text
    await update.message.reply_text("Ищу ответ...")

    try:
        answer = await ask_ai(user_id, question)
        save_message(user_id, "user", question)
        save_message(user_id, "assistant", answer)
    except Exception as e:
        answer = f"Произошла ошибка: {e}"

    await update.message.reply_text(answer)


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
