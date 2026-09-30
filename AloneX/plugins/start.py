import os
import aiohttp

from PIL import Image, ImageDraw, ImageFont

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_NAME, START_IMG_URL


CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def get_font(size, bold=False):
    try:
        return ImageFont.truetype(
            FONT_BOLD if bold else FONT_REGULAR,
            size
        )
    except Exception:
        return ImageFont.load_default()


async def download_image(url, path):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:

                if response.status != 200:
                    print("IMAGE DOWNLOAD ERROR:", response.status)
                    return False

                data = await response.read()

        with open(path, "wb") as f:
            f.write(data)

        return True

    except Exception as e:
        print("IMAGE DOWNLOAD ERROR:", e)
        return False


async def create_start_image(user_name):

    background = os.path.join(
        CACHE_DIR,
        "start_background.png"
    )

    output = os.path.join(
        CACHE_DIR,
        f"start_{abs(hash(user_name))}.png"
    )

    # Download START_IMG_URL
    ok = await download_image(
        START_IMG_URL,
        background
    )

    if not ok:
        return None

    try:
        image = Image.open(background).convert("RGBA")
        image = image.resize((1600, 900))

        draw = ImageDraw.Draw(image)

        # -----------------------------------------
        # USER NAME
        # -----------------------------------------

        name_font = get_font(32, True)

        display_name = user_name

        if len(display_name) > 20:
            display_name = display_name[:18] + "..."

        # Existing name area cover
        draw.rounded_rectangle(
            (990, 370, 1360, 455),
            radius=15,
            fill=(12, 5, 30, 245)
        )

        # Hello
        draw.text(
            (1010, 378),
            "Hello,",
            font=get_font(24),
            fill=(220, 210, 230)
        )

        # User name
        draw.text(
            (1010, 410),
            display_name,
            font=name_font,
            fill=(255, 255, 255)
        )

        image.save(output)

        return output

    except Exception as e:
        print("IMAGE EDIT ERROR:", e)
        return None


@Client.on_message(filters.command("start"))
async def start_command(client, message):

    user = message.from_user

    if not user:
        return

    # User name
    user_name = user.first_name or "User"

    if user.last_name:
        user_name += f" {user.last_name}"

    # Bot name
    bot_name = BOT_NAME.strip()

    # -----------------------------------------
    # CREATE IMAGE
    # -----------------------------------------

    start_image = await create_start_image(
        user_name
    )

    # -----------------------------------------
    # BUTTONS
    # -----------------------------------------

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✦ Help",
                    callback_data="help_menu"
                ),
                InlineKeyboardButton(
                    "⚙️ Settings",
                    callback_data="settings"
                )
            ],
            [
                InlineKeyboardButton(
                    "📢 Updates",
                    url="https://t.me/EikoUpdates"
                ),
                InlineKeyboardButton(
                    "💬 Support",
                    url="https://t.me/antidote_69"
                )
            ]
        ]
    )

    caption = (
        f"╭───〔 ✦ **{bot_name}** 〕───╮\n\n"
        f"👋 **Hello {user_name}!**\n\n"
        f"✨ Welcome to the bot.\n"
        f"⚡ Fast • Secure • Powerful\n\n"
        f"Use the buttons below to explore."
    )

    # -----------------------------------------
    # SEND IMAGE
    # -----------------------------------------

    if start_image and os.path.exists(start_image):

        try:
            await message.reply_photo(
                photo=start_image,
                caption=caption,
                reply_markup=buttons
            )

        except Exception as e:
            print("SEND IMAGE ERROR:", e)

            # Fallback
            await message.reply_photo(
                photo=START_IMG_URL,
                caption=caption,
                reply_markup=buttons
            )

        finally:
            try:
                os.remove(start_image)
            except Exception:
                pass

    else:

        # If image creation/download fails
        print("START IMAGE NOT CREATED")

        await message.reply_photo(
            photo=START_IMG_URL,
            caption=caption,
            reply_markup=buttons
        )
