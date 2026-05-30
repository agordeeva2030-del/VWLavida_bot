import os
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Читаем документ при запуске
with open("document.md", "r", encoding="utf-8") as f:
    DOCUMENT = f.read()

SYSTEM_PROMPT = f"""Ты — помощник по руководству эксплуатации автомобиля Volkswagen Lavida 2022.
Отвечай ТОЛЬКО на основе документа ниже. Если ответа в документе нет — так и скажи.
Отвечай по-русски, кратко и по делу.

ДОКУМЕНТ:
{DOCUMENT}
"""

async def ask_ai(question: str) -> str:
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
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
            },
        )
        data = response.json()
        if "choices" not in data:
            return f"Ошибка API: {data.get('error', {}).get('message', str(data))}"
        return data["choices"][0]["message"]["content"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я помогу найти информацию по руководству VW Lavida 2022.\n\n"
        "Задайте любой вопрос, например:\n"
        "• Что означает красная лампа масла?\n"
        "• Как включить задний противотуманный фонарь?\n"
        "• Как отрегулировать сиденье?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_question = update.message.text
    await update.message.reply_text("🔍 Ищу ответ...")

    try:
        answer = await ask_ai(user_question)
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
