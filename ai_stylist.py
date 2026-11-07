# --- ПРИЙОМ НОВИХ ФОТО З ОРГАНІЗАЦІЄЮ ПОЛИЧОК КНОПКАМИ 🌸 ---

@dp.message_handler(content_types=['photo'], state="*")
async def handle_clothing_photo(message: types.Message):
    user_id = message.from_user.id
    photo = message.photo[-1]
    
    # Створюємо зручні інлайн-кнопки для вибору правильної полички
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👚 Верх (Худі, куртка, топ)", callback_data=f"setcat_верх_{photo.file_id}"),
        InlineKeyboardButton("👖 Низ (Штани, джинси, спідниця)", callback_data=f"setcat_низ_{photo.file_id}"),
        InlineKeyboardButton("👟 Взуття (Кросівки, туфлі)", callback_data=f"setcat_взуття_{photo.file_id}"),
        InlineKeyboardButton("👜 Аксесуари (Сумочка, прикраси)", callback_data=f"setcat_аксесуари_{photo.file_id}")
    )
    
    await message.reply(
        "✨ **Яка красива річ!** 🥰\n"
        "На яку поличку твого віртуального гардероба ми її покладемо? Обери кнопку нижче: 👇",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query_handler(types.CallbackQuery.filter(Text(startswith="setcat_")), state="*")
async def save_clothing_with_exact_category(callback_query: types.CallbackQuery):
    _, category, file_id = callback_query.data.split("_")
    user_id = callback_query.from_user.id
    
    # Встановлюємо красиві естетичні текстові описи під кожну поличку
    if category == "верх":
        description = "Ніжне базове оверсайз худі або топ пастельного відтінку."
    elif category == "низ":
        description = "Естетичні базові штани джинси прямого крою у стилі Pinterest."
    elif category == "взуття":
        description = "Стильні повсякденні кросівки або естетичне взуття."
    else:
        description = "Витончений аксесуар або сумочка для завершення образу."
        
    # Надійно записуємо в базу даних на правильну поличку!
    database.add_clothing(user_id=user_id, file_id=file_id, description=description)
    
    # Примусово оновлюємо категорію в базі для залізобетонної надійності
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE clothes SET category = %s WHERE file_id = %s AND user_id = %s', (category, file_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    await callback_query.answer("Додано на поличку! 🌸")
    await callback_query.message.edit_text(
        f"✨ **Ура! Річ успішно додано на поличку '{category.upper()}'!** 🛍️\n\n"
        f"Тепер вона точно братиме участь у твоїх естетичних підборах образу! 🎀",
        parse_mode="Markdown"
    )
