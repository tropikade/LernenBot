import asyncio
import io
import os
import pandas as pd
from aiogram import Bot
from PIL import Image, ImageDraw, ImageFont
import edge_tts

# ================= НАСТРОЙКИ =================
# Токен берется из защищенных секретов GitHub
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@LernenDeutschland"  # Ваше имя канала
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/18O6oltKwgrr6wVK5R7P_2dCTGK0ukWSG/export?format=csv"
# =============================================

bot = Bot(token=BOT_TOKEN)

def create_card_image(word, translation, forms, example, level):
    img = Image.new('RGB', (1080, 1080), color='#1E1E2E')
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 70)
        font_sub = ImageFont.truetype("arial.ttf", 45)
        font_text = ImageFont.truetype("arial.ttf", 35)
    except:
        font_title = font_sub = font_text = ImageFont.load_default()

    draw.text((80, 80), f"Уровень: #{level}", fill='#F5E0DC', font=font_sub)
    draw.text((80, 200), str(word), fill='#89B4FA', font=font_title)
    draw.text((80, 320), str(translation), fill='#A6E3A1', font=font_sub)
    draw.line((80, 420, 1000, 420), fill='#585B70', width=3)
    
    if pd.notna(forms) and str(forms).strip() and str(forms) != 'nan':
        draw.text((80, 480), "Формы:", fill='#F38BA8', font=font_sub)
        draw.text((80, 550), str(forms), fill='#CDD6F4', font=font_text)
    
    if pd.notna(example) and str(example).strip() and str(example) != 'nan':
        draw.text((80, 680), "Пример:", fill='#F9E2AF', font=font_sub)
        draw.text((80, 750), str(example), fill='#CDD6F4', font=font_text)

    draw.text((80, 950), "@LernenDeutschland", fill='#6C7086', font=font_text)

    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio

async def generate_audio(text):
    communicate = edge_tts.Communicate(text, "de-DE-ConradNeural")
    bio = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            bio.write(chunk["data"])
    bio.seek(0)
    return bio

async def main():
    if not BOT_TOKEN:
        print("Ошибка: BOT_TOKEN не найден в Secrets!")
        return

    df = pd.read_csv(SHEET_CSV_URL)
    if df.empty:
        print("Таблица пуста!")
        return

    row = df.sample(n=1).iloc[0]
    post_type = str(row.get('type', 'verb'))

    if post_type == 'quiz':
        question = str(row['question'])
        options = str(row['options']).split('|')
        correct_option_text = str(row['correct']).strip()
        correct_id = options.index(correct_option_text) if correct_option_text in options else 0

        await bot.send_poll(
            chat_id=CHANNEL_ID,
            question=f"🧠 [{row['level']}] {question}",
            options=options,
            type='quiz',
            correct_option_id=correct_id,
            is_anonymous=True
        )
    else:
        word = str(row['word'])
        translation = str(row['translation'])
        forms = str(row['forms']) if pd.notna(row['forms']) and str(row['forms']) != 'nan' else ""
        example = str(row['example']) if pd.notna(row['example']) and str(row['example']) != 'nan' else ""
        level = str(row['level'])

        img_bytes = create_card_image(word, translation, forms, example, level)
        audio_text = f"{word}. {forms}. {example}"
        audio_bytes = await generate_audio(audio_text)

        caption = (
            f"🇩🇪 <b>{word}</b> — {translation}\n\n"
            f"📌 <b>Формы:</b> {forms}\n"
            f"💬 <b>Пример:</b> {example}\n\n"
            f"📊 Уровень: #{level}\n"
            f"🔗 @LernenDeutschland"
        )

        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=io.BytesIO(img_bytes.getvalue()),
            caption=caption,
            parse_mode="HTML"
        )

        await bot.send_voice(
            chat_id=CHANNEL_ID,
            voice=io.BytesIO(audio_bytes.getvalue()),
            caption=f"🔊 Произношение: {word}"
        )

    await (await bot.get_session()).close()

if __name__ == "__main__":
    asyncio.run(main())
