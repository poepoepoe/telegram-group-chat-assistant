from aiogram import Bot,Dispatcher,F,types
from aiogram.filters import Command
import asyncio
from dotenv import load_dotenv
import os
import logging
from openai import AsyncOpenAI

load_dotenv()   
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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

history = {
    # chat_id: [{"role": "user", "content": "..."}]
}


bot = Bot(token = bot_token)
dp = Dispatcher()


@dp.message()
async def handle_mentions(message: types.Message):

    if not message.text:
        return
    
    text = message.text

    chat_id = message.chat.id
    user_name =  message.from_user.username

    history.setdefault(chat_id, []).append({"role": "user", "content": f"{user_name}:{text}"})

    bot_mentioned =  f"@{bot_name}" in text

    if bot_mentioned:
        try:
            response_text = await generate_ai_response(chat_id)
            history[chat_id].append({"role": "assistant", "content": response_text})
            await message.reply(response_text)
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            await message.reply("Произошла ошибка при генерации ответа. Попробуйте позже.")
            return
    
    await summarize_history(chat_id)

    return


async def generate_ai_response(chat_id):

    messages = [{"role": "system", "content": system_prompt},
                *history[chat_id]]

    completion = await client.chat.completions.create(
    model=f"gpt://{folder}/{model}",
    messages=messages
    )
    
    response_text = completion.choices[0].message.content
    return response_text


async def summarize_history(chat_id):
    if len(history[chat_id]) < MAX_HISTORY:  
        return
    old_messages = history[chat_id][:-KEEP_RECENT]  
    if not old_messages:
        return
    prompt = system_prompt + "\n".join([f"{m['role']}: {m['content']}" for m in old_messages])
    completion = await client.chat.completions.create(
        model=f"gpt://{folder}/{model}",
        messages=[{"role": "user", "content": prompt}]
    )
    summary = completion.choices[0].message.content
    history[chat_id] = [{"role": "system", "content": summary}] + history[chat_id][-KEEP_RECENT:]      

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())