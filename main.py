from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
import asyncio
from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()
api_key = os.getenv("YANDEX_CLOUD_API_KEY")
folder = os.getenv("YANDEX_CLOUD_FOLDER")
model = os.getenv("YANDEX_CLOUD_MODEL")
bot_token = os.getenv("BOT_TOKEN")
bot_username = os.getenv("BOT_USERNAME")
system_prompt = os.getenv("SYSTEM_PROMPT")

MAX_HISTORY = 20
SUMMARY_LENGTH = 100

client = OpenAI(
    api_key=api_key, base_url="https://ai.api.cloud.yandex.net/v1", project=folder
)

history = {
    # chat_id: [{"role": "user", "content": "..."}]
}


bot = Bot(token=bot_token)
dp = Dispatcher()


@dp.message()
async def handle_mentions(message: types.Message):

    if not message.text:
        return

    text = message.text
    print(text)

    chat_id = message.chat.id
    user_name = message.from_user.username

    history.setdefault(chat_id, []).append(
        {"role": "user", "content": f"{user_name}:{text}"}
    )

    history[chat_id] = history[chat_id][-MAX_HISTORY:]

    bot_mentioned = f"@{bot_username}" in text

    if bot_mentioned:
        response_text = generate_ai_response(chat_id)
        history[chat_id].append({"role": "assistant", "content": response_text})
        await message.reply(response_text)

    summarize_history(chat_id)

    return


def generate_ai_response(chat_id):

    messages = [{"role": "system", "content": system_prompt}, *history[chat_id]]

    completion = client.chat.completions.create(
        model=f"gpt://{folder}/{model}", messages=messages
    )

    response_text = completion.choices[0].message.content
    return response_text


def summarize_history(chat_id):
    if len(history[chat_id]) < MAX_HISTORY:
        return
    old_messages = history[chat_id][:-10]
    if not old_messages:
        return
    prompt = f"""Суммаризируй эту беседу. Оставь важные детали. 
    Размер саммари ограничено {SUMMARY_LENGTH} словами.\n""" + "\n".join(
        [f"{m['role']}: {m['content']}" for m in old_messages]
    )
    completion = client.chat.completions.create(
        model=f"gpt://{folder}/{model}", messages=[{"role": "user", "content": prompt}]
    )
    summary = completion.choices[0].message.content
    history[chat_id] = [{"role": "system", "content": summary}] + history[chat_id][-10:]


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
