import asyncio
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import re

TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

videos = {}

def extract_video_id(url: str):
    match = re.search(r"video/(\d+)", url)
    return match.group(1) if match else None

async def get_tiktok_views(video_id: str):
    url = f"https://www.tikwm.com/api/?url=video/{video_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            try:
                return data["data"]["play_count"]
            except:
                return None

@dp.message(Command("start"))
async def start_cmd(msg: Message):
    await msg.answer("👋 Пришли ссылку на TikTok — я начну следить за просмотрами.\n/list — список видео")

@dp.message(Command("list"))
async def list_videos(msg: Message):
    user_videos = {vid: data for vid, data in videos.items() if data["chat_id"] == msg.chat.id}
    if not user_videos:
        await msg.answer("📭 Нет отслеживаемых видео")
        return
    for vid, data in user_videos.items():
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_{vid}")]
            ]
        )
        await msg.answer(f"🎬 {data['url']}\n👀 {data['views']:,}", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("del_"))
async def delete_video(callback: CallbackQuery):
    video_id = callback.data.replace("del_", "")
    if video_id in videos and videos[video_id]["chat_id"] == callback.message.chat.id:
        del videos[video_id]
        await callback.message.edit_text(f"✅ Удалено")
        await callback.answer("Удалено")

@dp.message()
async def handle_link(msg: Message):
    url = msg.text.strip()
    video_id = extract_video_id(url)
    if not video_id:
        await msg.answer("❌ Не ссылка на TikTok")
        return
    views = await get_tiktok_views(video_id)
    if views is None:
        await msg.answer("❌ Не удалось получить просмотры")
        return
    videos[video_id] = {
        "views": views,
        "chat_id": msg.chat.id,
        "last_notified": views,
        "url": url
    }
    await msg.answer(f"✅ Добавлено! {views:,} просмотров")

async def check_views_loop():
    await asyncio.sleep(10)
    while True:
        for video_id, data in list(videos.items()):
            new_views = await get_tiktok_views(video_id)
            if new_views and new_views - data["last_notified"] >= 3000:
                await bot.send_message(
                    data["chat_id"],
                    f"🔥 {data['url']}\n📈 +{new_views - data['last_notified']:,}\n👀 {new_views:,}"
                )
                videos[video_id]["last_notified"] = new_views
            if new_views:
                videos[video_id]["views"] = new_views
        await asyncio.sleep(600)

async def main():
    asyncio.create_task(check_views_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())