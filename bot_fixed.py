import asyncio
from typing import List
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

# 1. Мідлвар для збору альбому (Media Group) в один список
class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: float = 0.5):
        self.latency = latency
        self.albums = {}
        super().__init__()

    async def on_pre_process_message(self, message: types.Message, data: dict):
        if not message.media_group_id:
            return

        try:
            self.albums[message.media_group_id].append(message)
            raise CancelHandler()  # Скасовуємо обробку окремих фото з альбому
        except KeyError:
            self.albums[message.media_group_id] = [message]
            await asyncio.sleep(self.latency)
            data["album"] = self.albums.pop(message.media_group_id)

# 2. Ініціалізація бота
bot = Bot(token="ТВІЙ_ТЕЛЕГРАМ_ТОКЕН")
dp = Dispatcher(bot)
dp.middleware.setup(AlbumMiddleware())

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_wardrobe_photos(message: types.Message, album: list = None):
    # Збираємо всі фото з альбому
    photos_to_process = album if album else [message]
    
    status_msg = await message.reply("⏳ Аналізую кожну річ окремо, зачекай хвилинку...")
    final_results = []
    
    # Перебираємо кожну картинку по черзі
    for index, photo_msg in enumerate(photos_to_process, start=1):
        # Беремо ID саме ПОТОЧНОЇ картинки з циклу
        file_id = photo_msg.photo[-1].file_id
        
        try:
            # Завантажуємо файл
            file_info = await bot.get_file(file_id)
            
            # Передаємо в ai_stylist конкретну картинку
            description = await ai_stylist.analyze_image(file_info.file_path)
            
            final_results.append(f"✨ **Річ №{index}**:\n{description}\n")
        except Exception as e:
            final_results.append(f"❌ Не вдалося розпізнати річ №{index}: {str(e)}")
            
    # Виводимо один спільний звіт, де у кожної речі буде СВІЙ опис
    await status_msg.edit_text("\n".join(final_results))
