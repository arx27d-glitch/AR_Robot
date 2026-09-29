import asyncio
import logging

from pyrogram import filters, enums
from pyrogram.types import (
    InlineKeyboardButton as IKB,
    InlineKeyboardMarkup as IKM,
    Message,
    CallbackQuery,
)
from pyrogram.enums import ButtonStyle, ChatMemberStatus

from AloneX import pbot, prefix_cmds, font, init_aiohttp_session
import AloneX
from AloneX.helpers.decorator import protected_ids
from AloneX.db.chatbot import add_chat, remove_chat, CHAT_IDS
import config


__module__ = "𝐂ʜᴀᴛ-𝐁ᴏᴛ🤖"

__help__ = """
❂ *Chatbot Module* — A human-like AI chatbot.

*Commands:*
❂ /chatbot — Toggle chatbot in the current chat.

*Notes:*
• In groups, reply to or mention the bot.
• In private chat, the bot responds to messages when enabled.
• Supports English and Hinglish.
"""


logger = logging.getLogger(__name__)


# ============================================================
# ADMIN CHECK
# ============================================================

async def is_user_admin(chat_id: int, user_id: int) -> bool:

    if chat_id == user_id:
        return True

    if user_id in protected_ids:
        return True

    try:
        from AloneX.helpers.decorator import user_admin_cache

        cache_key = (chat_id, user_id, "a")

        if cache_key in user_admin_cache:
            return user_admin_cache[cache_key]

        member = await pbot.get_chat_member(chat_id, user_id)

        result = member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )

        user_admin_cache[cache_key] = result

        return result

    except Exception as e:
        logger.warning(f"Admin check error: {e}")
        return False


# ============================================================
# CHATBOT KEYBOARD
# ============================================================

async def get_chatbot_keyboard(chat_id: int):

    enabled = chat_id in CHAT_IDS

    if enabled:
        text = "🟢 Chatbot: ON"
        style = ButtonStyle.SUCCESS
    else:
        text = "🔴 Chatbot: OFF"
        style = ButtonStyle.DANGER

    return IKM(
        [
            [
                IKB(
                    font(text),
                    callback_data="chatbot_toggle",
                    style=style,
                )
            ]
        ]
    )


# ============================================================
# /CHATBOT COMMAND
# ============================================================

@pbot.on_message(
    filters.command("chatbot", prefixes=prefix_cmds)
)
async def chatbot_toggle_cmd(_, message: Message):

    if not message.from_user:
        return

    if not await is_user_admin(
        message.chat.id,
        message.from_user.id,
    ):
        return await message.reply_text(
            font("❌ You must be an admin to use this command.")
        )

    enabled = message.chat.id in CHAT_IDS

    status = "Enabled 🟢" if enabled else "Disabled 🔴"

    await message.reply_text(
        font(
            f"🤖 **Chatbot Status:** {status}\n\n"
            "When enabled, I will respond to mentions "
            "and replies with a human-like personality."
        ),
        reply_markup=await get_chatbot_keyboard(
            message.chat.id
        ),
    )


# ============================================================
# CALLBACK
# ============================================================

@pbot.on_callback_query(
    filters.regex(r"^chatbot_toggle$")
)
async def chatbot_toggle_callback(_, query: CallbackQuery):

    if not query.message:
        return

    user_id = query.from_user.id
    chat_id = query.message.chat.id

    if not await is_user_admin(chat_id, user_id):
        return await query.answer(
            font("❌ This button is for admins only!"),
            show_alert=True,
        )

    try:

        if chat_id in CHAT_IDS:

            await remove_chat(chat_id)

            if chat_id in CHAT_IDS:
                CHAT_IDS.remove(chat_id)

            new_state = False

        else:

            await add_chat(chat_id)

            if chat_id not in CHAT_IDS:
                CHAT_IDS.append(chat_id)

            new_state = True

        status = "Enabled 🟢" if new_state else "Disabled 🔴"

        await query.message.edit_text(
            font(
                f"🤖 **Chatbot Status:** {status}\n\n"
                "When enabled, I will respond to mentions "
                "and replies with a human-like personality."
            ),
            reply_markup=await get_chatbot_keyboard(chat_id),
        )

        await query.answer(
            font(
                f"Chatbot {'Enabled' if new_state else 'Disabled'}"
            )
        )

    except Exception as e:

        logger.error(
            f"Chatbot toggle error: {e}",
            exc_info=True,
        )

        await query.answer(
            font("❌ Something went wrong."),
            show_alert=True,
        )


# ============================================================
# AI PROMPT
# ============================================================

CHATBOT_PROMPT = """
Your name is 𖤍 ˹ ᴀʀ ꭙ ʙᴏᴛ ˼.

You are a friendly, cool and human-like AI chatbot.

Talk naturally like a real person.
Do not sound like a formal AI assistant.

You can speak:
• English
• Hinglish
• Hindi

Keep replies relatively short and engaging.

You can be:
• Friendly
• Helpful
• Slightly witty
• Natural

Use emojis occasionally.

If someone asks who created you,
say that you were created by Antidote.

Do not claim to be a human.
"""


# ============================================================
# GROQ AI
# ============================================================

async def get_chatbot_reply(text: str):

    if not text:
        return None

    try:

        if getattr(AloneX, "aiohttpsession", None) is None:
            await init_aiohttp_session()

        if not getattr(AloneX, "aiohttpsession", None):
            logger.error("aiohttp session is not available.")
            return None

        api_key = getattr(config, "GROQ_API_KEY", None)

        if not api_key:
            logger.error("GROQ_API_KEY is missing in config.py")
            return None

        api_url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model"=="openai/gpt-oss-120b",
            "messages": [
                {
                    "role": "system",
                    "content": CHATBOT_PROMPT,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            "temperature": 0.7,
            "max_tokens": 500,
        }

        async with AloneX.aiohttpsession.post(
            api_url,
            headers=headers,
            json=data,
        ) as response:

            response_text = await response.text()

            if response.status != 200:

                logger.error(
                    f"Groq API Error {response.status}: "
                    f"{response_text}"
                )

                return None

            try:
                result = await response.json()
            except Exception:

                logger.error(
                    f"Invalid JSON from Groq: {response_text}"
                )

                return None

            choices = result.get("choices")

            if not choices:
                logger.error(
                    f"Groq returned no choices: {result}"
                )
                return None

            reply = (
                choices[0]
                .get("message", {})
                .get("content")
            )

            if reply:
                return reply.strip()

    except asyncio.TimeoutError:

        logger.error("Groq API request timed out.")

    except Exception as e:

        logger.error(
            f"Chatbot AI Error: {e}",
            exc_info=True,
        )

    return None


# ============================================================
# CHATBOT MESSAGE HANDLER
# ============================================================

@pbot.on_message(
    (
        filters.text
        | filters.caption
    )
    & ~filters.bot
    & ~filters.command(
        [
            "chatbot",
            "alonex",
            "gpt",
            "groq",
            "google",
            "gemini",
        ]
    ),
    group=10,
)
async def chatbot_handler(_, message: Message):

    try:

        if not message.chat:
            return

        chat_id = message.chat.id

        if chat_id not in CHAT_IDS:
            return

        input_text = message.text or message.caption

        if not input_text:
            return

        input_text = input_text.strip()

        if not input_text:
            return

        # GROUP / SUPERGROUP
        if message.chat.type in (
            enums.ChatType.GROUP,
            enums.ChatType.SUPERGROUP,
        ):

            is_reply_to_bot = False

            if message.reply_to_message:

                replied_user = message.reply_to_message.from_user

                if replied_user:

                    if replied_user.is_self:
                        is_reply_to_bot = True

                    elif (
                        pbot.me
                        and pbot.me.username
                        and replied_user.username
                        and replied_user.username.lower()
                        == pbot.me.username.lower()
                    ):
                        is_reply_to_bot = True

            is_mentioned = bool(
                getattr(message, "mentioned", False)
            )

            if not (
                is_reply_to_bot
                or is_mentioned
            ):
                return

        # REMOVE BOT MENTION
        if pbot.me and pbot.me.username:

            username = pbot.me.username

            input_text = input_text.replace(
                f"@{username}",
                "",
            )

            input_text = input_text.replace(
                f"@{username.lower()}",
                "",
            )

            input_text = input_text.strip()

        # Only mention
        if not input_text:
            input_text = "Hello"

        # Typing
        try:
            await pbot.send_chat_action(
                chat_id,
                enums.ChatAction.TYPING,
            )
        except Exception:
            pass

        # Get AI reply
        reply = await get_chatbot_reply(input_text)

        if not reply:
            return

        # Send reply
        await message.reply_text(
            reply,
            disable_web_page_preview=True,
        )

    except Exception as e:

        logger.error(
            f"Chatbot handler error: {e}",
            exc_info=True,
            )
