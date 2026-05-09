from aiogram import Bot,Dispatcher,F,types
from aiogram.filters import Command
import asyncio
from dotenv import load_dotenv
import os
import logging
from openai import AsyncOpenAI

class ChatHistoryStore:
    def __init__(self):
        self.history = {}
    
    def add_message(self, chat_id, message):
        self.history.setdefault(chat_id, []).append(message)
    
    def get_history(self, chat_id):
        return self.history.get(chat_id, [])

    def delete_recent_messages(self, chat_id, keep_count):
        if len(self.history.get(chat_id, [])) <= keep_count:
            return
        self.history[chat_id] = self.history[chat_id][-keep_count:]


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    load_dotenv() 
except Exception as e:
    logger.error(f"Error loading environment variables: {e}")
    exit(1)

history_store = ChatHistoryStore()  


api_key = os.getenv("YANDEX_CLOUD_API_KEY")
folder = os.getenv("YANDEX_CLOUD_FOLDER")
model = os.getenv("YANDEX_CLOUD_MODEL")
bot_token = os.getenv("BOT_TOKEN")
bot_name = os.getenv("BOT_NAME")

with open("promts/system.txt", "r", encoding="utf-8") as file:
    system_prompt = file.read()

MAX_HISTORY = 20     
KEEP_RECENT = 10     
SUMMARY_LENGTH = 100

client = AsyncOpenAI(
  api_key=api_key,
  base_url="https://ai.api.cloud.yandex.net/v1",
  project=folder
)


bot = Bot(token = bot_token)
dp = Dispatcher()


@dp.message()
async def handle_mentions(message: types.Message):

    if not message.text:
        return
    
    text = message.text

    chat_id = message.chat.id
    user_name =  message.from_user.username

    history_store.add_message(chat_id, {"role": "user", "content": f"{user_name}:{text}"})

    bot_mentioned =  f"@{bot_name}" in text

    if bot_mentioned:
        try:
            response_text = await generate_ai_response(chat_id)
            history_store.add_message(chat_id, {"role": "assistant", "content": response_text})
            await message.reply(response_text)
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            await message.reply("Произошла ошибка при генерации ответа. Попробуйте позже.")
            return
    if len(history_store.get_history(chat_id)) > MAX_HISTORY:
        await summarize_history(chat_id)

    return


async def generate_ai_response(chat_id):

    messages = [{"role": "system", "content": system_prompt},
                *history_store.get_history(chat_id)]

    completion = await client.chat.completions.create(
    model=f"gpt://{folder}/{model}",
    messages=messages
    )
    
    response_text = completion.choices[0].message.content
    return response_text


async def summarize_history(chat_id):
    old_messages = history_store.get_history(chat_id)[:-KEEP_RECENT]  

    prompt = system_prompt + "\n".join([f"{m['role']}: {m['content']}" for m in old_messages])
    completion = await client.chat.completions.create(
        model=f"gpt://{folder}/{model}",
        messages=[{"role": "user", "content": prompt}]
    )
    summary = completion.choices[0].message.content
    history_store.add_message(chat_id, {"role": "system", "content": summary})      
    history_store.delete_recent_messages(chat_id, KEEP_RECENT)
    return summary

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())