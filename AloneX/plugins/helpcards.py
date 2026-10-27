"""
AloneX/plugins/helpcards.py

Help menu with pictures. Click a module button in /help and the commands come as a premium picture
(like the ADMIN COMMANDS one) instead of a text message.

* Works WITHOUT changing callbacks.py or base.py: these handlers run first (group -8). When a module has no
  picture (nothing to draw), they pass the click on and the old text help is shown as before.
* Admin: uses AloneX/helpers/data/help_cards/admin.jpg (your picture). Drop <name>.jpg/png into the same
  folder to give any other module its own picture.
* Other modules: drawn from their __help__ text (10 commands per picture, ⬅️ ➡️ buttons for more).
* /help <module> in private chat also answers with the picture (type it in plain letters: /help admin).
* Owner: /helpkeys shows every module, its plain name and what picture it gets.
"""
import hashlib
import logging
from typing import Dict, Optional

from pyrogram import filters
from pyrogram.errors import RPCError
from pyrogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM, InputMediaPhoto

import config
from AloneX import pbot, MODULE, font, prefix_cmds
from AloneX.helpers import help_card

log = logging.getLogger("AloneX.helpcards")

_GROUP = -8                       # runs before the normal help handlers (group 0 / 13)
_FILE_IDS: Dict[str, str] = {}    # picture -> Telegram file_id (sent once, reused afterwards)


# ───────────────────────── small helpers ─────────────────────────
def _sid(key: str) -> str:
    """Short id for a module key (callback_data is limited to 64 bytes and keys contain fancy letters)."""
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]


def _key_from_sid(sid: str) -> Optional[str]:
    for key in MODULE:
        if _sid(key) == sid:
            return key
    return None


def _find_key(name: str) -> Optional[str]:
    """/help admin -> the real module key ('𝐀ᴅᴍɪɴ🛠️')."""
    name = (name or "").strip()
    if name in MODULE:
        return name
    wanted = help_card.canon_key(name)
    if not wanted:
        return None
    for key in MODULE:
        if help_card.canon_key(key) == wanted:
            return key
    return None


def _caption(card: "help_card.Card") -> str:
    text = f"⚡ {card.title.title()} Commands"
    if card.pages > 1:
        text += f"  •  {card.page + 1}/{card.pages}"
    return font(text)


def _keyboard(key: str, card: "help_card.Card", uid: int) -> IKM:
    rows = []
    if card.pages > 1:
        sid = _sid(key)
        prev_p, next_p = (card.page - 1) % card.pages, (card.page + 1) % card.pages
        rows.append([
            IKB("⬅️", callback_data=f"hcard#{sid}#{prev_p}#{uid}"),
            IKB(f"{card.page + 1}/{card.pages}", callback_data="hcard#noop"),
            IKB("➡️", callback_data=f"hcard#{sid}#{next_p}#{uid}"),
        ])
    rows.append([IKB(font("🔄 Back"), callback_data=f"help_{uid}")])
    return IKM(rows)


def _remember(card: "help_card.Card", sent) -> None:
    fid = getattr(getattr(sent, "photo", None), "file_id", None)
    if fid:
        _FILE_IDS[card.cache_key] = fid


async def _card_for(key: str, page: int):
    try:
        return await help_card.get_card(key, MODULE.get(key, ""), page)
    except Exception:
        log.exception("help card could not be made for %r", key)
        return None


async def _show(client, query, key: str, card, uid: int) -> bool:
    """Replaces the clicked help message by the picture. Returns False if nothing could be shown."""
    kb, cap = _keyboard(key, card, uid), _caption(card)
    sources = ([_FILE_IDS[card.cache_key]] if card.cache_key in _FILE_IDS else []) + [card.path]

    for src in sources:  # normal case: the help message is a photo, swap it for the new picture
        try:
            sent = await query.edit_message_media(InputMediaPhoto(src, caption=cap), reply_markup=kb)
        except RPCError as e:
            if getattr(e, "ID", "") == "MESSAGE_NOT_MODIFIED":
                return True  # this picture is already shown
            log.info("edit_message_media failed (%s), trying another way", getattr(e, "ID", type(e).__name__))
            continue
        except Exception as e:
            log.info("edit_message_media failed (%s), trying another way", type(e).__name__)
            continue
        _remember(card, sent)
        return True

    # the help message was plain text (long help): send the picture as a new message, remove the old one
    for src in sources:
        try:
            sent = await client.send_photo(query.message.chat.id, src, caption=cap, reply_markup=kb)
        except Exception as e:
            log.info("send_photo failed (%s)", type(e).__name__)
            continue
        _remember(card, sent)
        try:
            await query.message.delete()
        except Exception:
            pass
        return True
    return False


# ───────────────────────── a module button was clicked ─────────────────────────
@pbot.on_callback_query(filters.regex(r"^help_[^_]+_\d+$"), group=_GROUP)
async def helpcard_open(client, query):
    parts = query.data.split("_")
    key = parts[1]
    uid = int(parts[2])
    if query.from_user.id != uid or key not in MODULE:
        query.continue_propagation()  # the normal handler answers ("not your button" etc.)
    card = await _card_for(key, 0)
    if card is None:
        query.continue_propagation()  # nothing to draw: old text help
    await query.answer(font("Opening..."))
    if not await _show(client, query, key, card, uid):
        query.continue_propagation()
    query.stop_propagation()


# ───────────────────────── ⬅️ ➡️ pages ─────────────────────────
@pbot.on_callback_query(filters.regex(r"^hcard#"), group=_GROUP)
async def helpcard_page(client, query):
    parts = query.data.split("#")
    if len(parts) < 4:
        return await query.answer()
    sid, uid = parts[1], int(parts[3])
    if query.from_user.id != uid:
        return await query.answer("⚠️ Don't trigger others commands!", show_alert=True)
    key = _key_from_sid(sid)
    card = await _card_for(key, int(parts[2])) if key else None
    if card is None:
        return await query.answer("Not found", show_alert=True)
    await query.answer()
    await _show(client, query, key, card, uid)


# ───────────────────────── /help <module> in private chat ─────────────────────────
@pbot.on_message(filters.command("help", prefixes=prefix_cmds) & filters.private, group=_GROUP)
async def helpcard_cmd(client, message):
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not message.from_user:
        message.continue_propagation()
    key = _find_key(args[1])
    if not key:
        message.continue_propagation()
    card = await _card_for(key, 0)
    if card is None:
        message.continue_propagation()
    sources = ([_FILE_IDS[card.cache_key]] if card.cache_key in _FILE_IDS else []) + [card.path]
    done = False
    for src in sources:
        try:
            sent = await message.reply_photo(src, caption=_caption(card),
                                             reply_markup=_keyboard(key, card, message.from_user.id))
        except Exception as e:
            log.info("help picture not sent (%s)", type(e).__name__)
            continue
        _remember(card, sent)
        done = True
        break
    if not done:
        message.continue_propagation()
    message.stop_propagation()


# ───────────────────────── owner: which module gets which picture ─────────────────────────
@pbot.on_message(filters.command("helpkeys", prefixes=prefix_cmds))
async def helpkeys_cmd(_, message):
    user = message.from_user
    if not user or user.id != getattr(config, "OWNER_ID", 0):
        return
    lines = ["Module | plain name | picture", ""]
    for key, text in MODULE.items():
        name = help_card.canon_key(key)
        if help_card.static_card_path(key):
            kind = "your picture"
        else:
            n = len(help_card.parse_commands(text))
            kind = f"drawn ({n} commands)" if n >= 2 else "text (no commands found)"
        lines.append(f"{help_card.display_name(key).title()} | {name} | {kind}")
    lines += ["", "Own picture for a module: put <plain name>.jpg in AloneX/helpers/data/help_cards/"]
    out = "\n".join(lines)
    for i in range(0, len(out), 3900):
        await message.reply_text(out[i:i + 3900], parse_mode=None)
