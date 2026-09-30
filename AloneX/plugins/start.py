import os
import asyncio
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_NAME, START_IMG_URL


# =========================================================
# SETTINGS
# =========================================================

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


# =========================================================
# FONT HELPER
# =========================================================

def get_font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REGULAR

    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# =========================================================
# CENTER TEXT
# =========================================================

def center_text(draw, text, y, font, width, fill=(255, 255, 255)):
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]

    x = (width - text_width) // 2

    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
        stroke_width=1,
        stroke_fill=(20, 10, 35)
    )


# =========================================================
# CREATE START IMAGE
# =========================================================

async def create_start_image(
    background_path: str,
    user_name: str,
    bot_name: str,
    user_photo: str = None
):

    output = os.path.join(
        CACHE_DIR,
        f"start_{abs(hash(user_name + bot_name))}.png"
    )

    # Background
    image = Image.open(background_path).convert("RGB")
    image = image.resize((1600, 900))

    draw = ImageDraw.Draw(image)

    # -----------------------------------------------------
    # Fonts
    # -----------------------------------------------------

    title_font = get_font(58, True)
    bot_font = get_font(42, True)
    user_font = get_font(32, True)
    small_font = get_font(25)

    # -----------------------------------------------------
    # Dark transparent panel
    # -----------------------------------------------------

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # Right side panel
    odraw.rounded_rectangle(
        (850, 95, 1515, 800),
        radius=35,
        fill=(8, 4, 25, 210),
        outline=(170, 70, 255, 220),
        width=4
    )

    # -----------------------------------------------------
    # Header
    # -----------------------------------------------------

    center_text(
        odraw,
        "WELCOME",
        145,
        title_font,
        1600,
        (255, 245, 255)
    )

    center_text(
        odraw,
        f"TO {bot_name}",
        220,
        bot_font,
        1600,
        (205, 90, 255)
    )

    center_text(
        odraw,
        "YOUR ALL-IN-ONE TELEGRAM BOT",
        285,
        small_font,
        1600,
        (220, 220, 230)
    )

    # -----------------------------------------------------
    # User box
    # -----------------------------------------------------

    odraw.rounded_rectangle(
        (925, 355, 1440, 470),
        radius=25,
        fill=(25, 10, 45, 230),
        outline=(180, 60, 255, 180),
        width=3
    )

    # User name
    display_name = user_name

    if len(display_name) > 22:
        display_name = display_name[:20] + "..."

    odraw.text(
        (1050, 375),
        "Hello,",
        font=get_font(25),
        fill=(220, 210, 230)
    )

    odraw.text(
        (1050, 410),
        display_name,
        font=user_font,
        fill=(255, 255, 255)
    )

    # -----------------------------------------------------
    # Features
    # -----------------------------------------------------

    features = [
        ("✦", "Fast Response"),
        ("✦", "Secure & Safe"),
        ("✦", "Premium Features"),
        ("✦", "24/7 Online"),
    ]

    x_positions = [910, 1050, 1190, 1330]

    for i, (icon, text) in enumerate(features):

        x = x_positions[i]

        odraw.rounded_rectangle(
            (x, 535, x + 110, 640),
            radius=18,
            outline=(160, 60, 255, 180),
            width=2
        )

        odraw.text(
            (x + 45, 545),
            icon,
            font=get_font(28, True),
            fill=(210, 90, 255)
        )

        # Short text
        short = text.split()[0]

        odraw.text(
            (x + 15, 590),
            short,
            font=get_font(18, True),
            fill=(240, 240, 250)
        )

    # -----------------------------------------------------
    # Bottom
    # -----------------------------------------------------

    center_text(
        odraw,
        "ENJOY YOUR JOURNEY",
        690,
        get_font(32, True),
        1600,
        (210, 90, 255)
    )

    center_text(
        odraw,
        f"Powered by {bot_name}",
        740,
        get_font(22),
        1600,
        (210, 200, 220)
    )

    # Merge
    image = Image.alpha_composite(
        image.convert("RGBA"),
        overlay
    )

    # -----------------------------------------------------
    # User profile photo
    # -----------------------------------------------------

    if user_photo and os.path.exists(user_photo):

        try:
            avatar = Image.open(user_photo).convert("RGBA")

            avatar_size = 82
            avatar = avatar.resize(
                (avatar_size, avatar_size)
            )

            # Circular mask
            mask = Image.new(
                "L",
                (avatar_size, avatar_size),
                0
            )

            mask_draw = ImageDraw.Draw(mask)

            mask_draw.ellipse(
                (0, 0, avatar_size, avatar_size),
                fill=255
            )

            avatar.putalpha(mask)

            image.alpha_composite(
                avatar,
                (945, 372)
            )

        except Exception:
            pass

    image.save(output)

    return output


# =========================================================
# START COMMAND
# =========================================================

@Client.on_message(filters.command("start"))
async def start_command(client, message):

    user = message.from_user

    if not user:
        return

    # User name
    user_name = user.first_name or "User"

    if user.last_name:
        user_name += f" {user.last_name}"

    # -----------------------------------------------------
    # Bot name
    # -----------------------------------------------------

    bot_name = BOT_NAME

    # Remove fancy extra spaces if needed
    bot_name = bot_name.strip()

    # -----------------------------------------------------
    # Download user's profile photo
    # -----------------------------------------------------

    user_photo = None

    try:

        photos = []

        async for photo in client.get_chat_photos(
            user.id,
            limit=1
        ):
            photos.append(photo)

        if photos:

            user_photo = await client.download_media(
                photos[0].file_id,
                file_name=f"{CACHE_DIR}/{user.id}_avatar"
            )

    except Exception:
        user_photo = None

    # -----------------------------------------------------
    # Background
    # -----------------------------------------------------

    background = "assets/start_ui.png"

    if not os.path.exists(background):
        await message.reply_text(
            "❌ Start image not found.\n\n"
            "Put your generated image here:\n"
            "`assets/start_ui.png`"
        )
        return

    # -----------------------------------------------------
    # Generate image
    # -----------------------------------------------------

    try:

        start_image = await create_start_image(
            background_path=background,
            user_name=user_name,
            bot_name=bot_name,
            user_photo=user_photo
        )

    except Exception as e:

        print(f"START IMAGE ERROR: {e}")

        await message.reply_text(
            f"👋 Hello {user_name}!\n\n"
            f"Welcome to {bot_name}."
        )

        return

    # -----------------------------------------------------
    # Buttons
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Send
    # -----------------------------------------------------

    await message.reply_photo(
        photo=start_image,
        caption=(
            f"╭───〔 ✦ **{bot_name}** 〕───╮\n\n"
            f"👋 **Hello {user_name}!**\n\n"
            f"✨ Welcome to the bot.\n"
            f"⚡ Fast • Secure • Powerful\n\n"
            f"Use the buttons below to explore."
        ),
        reply_markup=buttons
    )

    # -----------------------------------------------------
    # Cleanup
    # -----------------------------------------------------

    try:

        if user_photo and os.path.exists(user_photo):
            os.remove(user_photo)

        if os.path.exists(start_image):
            os.remove(start_image)

    except Exception:
        pass
