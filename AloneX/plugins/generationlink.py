from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import (
    ChatAdminRequired,
    PeerIdInvalid,
    ChannelInvalid,
)
from AloneX import pbot, DEV_LIST, font
from AloneX import database2 as database


# =========================================================
# DATABASE
# =========================================================

collection = database["chats"]


# =========================================================
# GENERATE CHAT LINK
# =========================================================

@pbot.on_message(
    filters.command("generatelink", prefixes=["/", "!"])
    & filters.user(DEV_LIST)
)
async def generate_link_cmd(_, message: Message):

    # -----------------------------------------------------
    # Check command arguments
    # -----------------------------------------------------

    if len(message.command) < 2:
        return await message.reply_text(
            "❌ Usage: `/generatelink -100xxxxxxxxxx`"
        )

    # -----------------------------------------------------
    # Convert chat ID
    # -----------------------------------------------------

    try:
        chat_id = int(message.command[1])

    except (ValueError, TypeError):
        return await message.reply_text(
            font("❌ Invalid chat ID format.")
        )

    # -----------------------------------------------------
    # Find chat in database
    # -----------------------------------------------------

    try:
        chat = await collection.find_one({
            "chat_id": chat_id
        })

    except Exception:
        return await message.reply_text(
            font("❌ Database error while finding the chat.")
        )

    if not chat:
        return await message.reply_text(
            font("⚠️ Chat not found in database.")
        )

    # -----------------------------------------------------
    # PUBLIC CHAT
    # -----------------------------------------------------

    if chat.get("chat_username"):
        username = str(chat["chat_username"]).lstrip("@")

        return await message.reply_text(
            f"🔗 **Public Link:**\n"
            f"https://t.me/{username}"
        )

    # -----------------------------------------------------
    # PRIVATE CHAT
    # -----------------------------------------------------

    try:
        link = await pbot.export_chat_invite_link(chat_id)

        return await message.reply_text(
            f"🔗 **Invite Link:**\n{link}"
        )

    # -----------------------------------------------------
    # BOT IS NOT ADMIN
    # -----------------------------------------------------

    except ChatAdminRequired:
        return await message.reply_text(
            font(
                "🚫 The bot must be an **admin** in this chat "
                "to generate an invite link."
            )
        )

    # -----------------------------------------------------
    # BOT IS NOT MEMBER / INVALID PEER
    # -----------------------------------------------------

    except PeerIdInvalid:
        return await message.reply_text(
            font(
                "🚫 The bot is not a member of that chat "
                "or the chat ID is invalid."
            )
        )

    # -----------------------------------------------------
    # INVALID CHAT
    # -----------------------------------------------------

    except ChannelInvalid:
        return await message.reply_text(
            font(
                "🚫 Invalid channel or chat ID."
            )
        )

    # -----------------------------------------------------
    # OTHER ERRORS
    # -----------------------------------------------------

    except Exception as e:
        return await message.reply_text(
            font(
                "❌ Unexpected error while creating the link."
            )
        )
