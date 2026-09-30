import os
import aiohttp

from PIL import Image, ImageDraw, ImageFont

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_NAME, START_IMG


# =========================
# FONT
# =========================

def get_font(size):
    fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]

    for font in fonts:
        if os.path.exists(font):
            return ImageFont.truetype(font, size)

    return ImageFont.load_default()


# =========================
# DOWNLOAD IMAGE
# =========================

async def download_image(url, filename):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return False

            data = await response.read()

            with open(filename, "wb") as f:
                f.write(data)

    return True


# =========================
# CREATE START IMAGE
# =========================

def create_start_image(input_file, output_file, user_name):

    image = Image.open(input_file).convert("RGB")

    draw = ImageDraw.Draw(image)

    width, height = image.size

    # Fonts
    bot_font = get_font(int(width * 0.045))
    user_font = get_font(int(width * 0.032))

    # =========================
    # BOT NAME
    # =========================

    draw.text(
        (width // 2, int(height * 0.80)),
        BOT_NAME,
        font=bot_font,
        fill="white",
        anchor="mm",
        stroke_width=2,
        stroke_fill="black",
    )

    # =========================
    # USER NAME
    # =========================

    draw.text(
        (width // 2, int(height * 0.88)),
        f"Welcome, {user_name}",
        font=user_font,
        fill="white",
        anchor="mm",
        stroke_width=2,
        stroke_fill="black",
    )

    image.save(output_file, quality=95)

    return output_file


# =========================
# START COMMAND
# =========================

@Client.on_message(filters.command("start"))
async def start_command(client, message):

    user = message.from_user

    if not user:
        return

    user_name = user.first_name or "User"

    original_image = "start_original.jpg"
    final_image = "start_final.jpg"

    try:

        # Download START_IMG
        downloaded = await download_image(
            START_IMG,
            original_image
        )

        if not downloaded:
            await message.reply_text(
                "❌ Start image download nahi ho payi."
            )
            return

        # Create edited image
        create_start_image(
            original_image,
            final_image,
            user_name
        )

        # Get bot username
        me = await client.get_me()

        bot_username = me.username

        # Buttons
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "➕ Add Me",
                        url=f"https://t.me/{bot_username}?startgroup=true"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📚 Help",
                        callback_data="help"
                    ),
                    InlineKeyboardButton(
                        "📢 Updates",
                        url="https://t.me/your_channel"
                    )
                ]
            ]
        )

        # Send image
        await message.reply_photo(
            photo=final_image,
            caption=f"**{BOT_NAME}**\n\n"
                    f"👋 Hello {user_name}!",
            reply_markup=buttons
        )

    except Exception as e:

        print(f"START ERROR: {e}")

        await message.reply_text(
            f"❌ Start Error:\n`{e}`"
        )

    finally:

        # Delete temporary files
        for file in [original_image, final_image]:

            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass
