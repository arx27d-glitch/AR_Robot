import base64
import asyncio
import config
import logging
import random
import time
import os
import hashlib
from datetime import datetime
from collections import defaultdict, deque
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont

from pyrogram import enums, types, Client, filters
from pyrogram.enums import ButtonStyle
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import (
    FloodWait,
    UserIsBlocked,
    InputUserDeactivated,
    BadRequest,
    RPCError
)

from AloneX import (
    MODULE,
    pbot,
    SUPPORT_CHAT,
    LOGS_CHANNEL,
    UPDATE_CHANNEL,
    BOT_USERNAME,
    prefix_cmds,
    font
)

from AloneX.db.users import (
    add_user,
    get_user_join_source,
    activate_user
)

from AloneX.db.chats import check_chat_exists
from AloneX.db.autofilter import get_file_by_index
from AloneX.helpers.misc import get_help_button
from AloneX.helpers.utils import (
    autofilter_send_file,
    decode_to_base64,
    auto_delete,
    time_formatter
)
from AloneX.helpers.pyro_utils import check_membership, no_channel
from AloneX.db.rules import get_rules
from AloneX.plugins.rules import DEFAULT_MESSAGE
from AloneX.plugins.adminpanel import handle_admin_deeplink
from AloneX.plugins.settings import handle_settings_deeplink


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


# ============================================================
# CACHE / GLOBALS
# ============================================================

_user_cache = {}
_chat_cache = {}
_rules_cache = {}
_file_cache = {}
_chat_name_cache = {}
_membership_cache = {}
_user_request_times = {}

_request_queue = deque(maxlen=500)

_db_write_queue = []
_db_write_lock = asyncio.Lock()

_log_queue = []
_log_lock = asyncio.Lock()

_pending_tasks = {}

MAX_REQ_PER_SEC = 1000
USER_COOLDOWN = 0.00001
BATCH_INTERVAL = 0.05
CACHE_TTL = 3600
PRELOAD_ENABLED = True


# ============================================================
# START EFFECTS
# ============================================================

START_EFFECTS = {
    '👍': 5107584321108051014,
    '👎': 5104858069142078462,
    '❤': 5159385139981059251,
    '🔥': 5104841245755180586,
    '🎉': 5046509860389126442,
    '💩': 5046589136895476101
}

EFFECT_VALUES = list(START_EFFECTS.values())

BOT_UN = BOT_USERNAME.lstrip('@')

SE = (
    5107584321108051014,
    5104858069142078462,
    5159385139981059251,
    5104841245755180586,
    5046509860389126442,
    5046589136895476101
)

_SB = None
_bi = None
_tr = None


_user_queue = asyncio.Queue()
_processing_users = set()
_last_process_time = defaultdict(float)

_semaphore = asyncio.Semaphore(15000)

_queue_processor_started = False

_cmd_cache = defaultdict(dict)
_cache_expiry = 3600


# ============================================================
# START IMAGE SETTINGS
# ============================================================

START_IMAGE_CACHE_DIR = "start_image_cache"

try:
    os.makedirs(START_IMAGE_CACHE_DIR, exist_ok=True)
except Exception:
    pass


def _start_image_cache_path():
    """
    URL ke hisaab se alag cache file banata hai.
    Isliye URL change karne par purani image use nahi hogi.
    """
    try:
        url = getattr(
            config,
            "START_IMG_URL",
            "https://litter.catbox.moe/m56fbg.jpg"
        )

        url_hash = hashlib.md5(
            url.encode("utf-8")
        ).hexdigest()[:16]

        return os.path.join(
            START_IMAGE_CACHE_DIR,
            f"start_{url_hash}.jpg"
        )

    except Exception:
        return os.path.join(
            START_IMAGE_CACHE_DIR,
            "start_default.jpg"
        )


def _get_start_font(size):
    """
    Server par available font dhoondta hai.
    """

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]

    for path in font_paths:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            pass

    return ImageFont.load_default()


async def _download_start_image():
    """
    START_IMG_URL se original image download karta hai.
    """

    try:
        url = getattr(
            config,
            "START_IMG_URL",
            "https://litter.catbox.moe/m56fbg.jpg"
        )

        cache_path = _start_image_cache_path()

        if os.path.exists(cache_path):
            return cache_path

        def _download():
            with urlopen(url, timeout=30) as response:
                data = response.read()

            with open(cache_path, "wb") as f:
                f.write(data)

        await asyncio.to_thread(_download)

        if os.path.exists(cache_path):
            return cache_path

        return None

    except Exception as e:
        print(f"[START IMAGE DOWNLOAD ERROR] {e}")
        return None


async def _make_start_image(user_name):
    """
    Original START image ko edit karta hai.

    Old:
        Hello, AR_X
        Shadow_Mona

    New:
        Hello, USER NAME

    Name ke peeche transparent dark overlay rahega.
    """

    try:
        source = await _download_start_image()

        if not source:
            return None

        def _create():

            img = Image.open(source).convert("RGBA")

            # Original image ka ratio maintain
            width, height = img.size

            draw = ImageDraw.Draw(img, "RGBA")

            # ------------------------------------------------
            # IMAGE IS 1536x1024
            # Agar future mein size different ho to coordinates
            # automatically scale honge.
            # ------------------------------------------------

            sx = width / 1536
            sy = height / 1024

            def scx(x):
                return int(x * sx)

            def scy(y):
                return int(y * sy)

            # ------------------------------------------------
            # OLD USER NAME AREA COVER
            #
            # Original image mein:
            # Hello, 👑 AR_X
            # Shadow_Mona etc.
            #
            # Us area ko transparent dark overlay se cover kar
            # rahe hain.
            # ------------------------------------------------

            left = scx(975)
            top = scy(355)
            right = scx(1385)
            bottom = scy(465)

            draw.rounded_rectangle(
                (left, top, right, bottom),
                radius=scx(18),
                fill=(5, 3, 15, 185),
                outline=(150, 55, 255, 150),
                width=max(1, scx(2))
            )

            # ------------------------------------------------
            # USER NAME
            # ------------------------------------------------

            display_name = str(
                user_name or "User"
            ).strip()

            if not display_name:
                display_name = "User"

            # Long name ko limit
            if len(display_name) > 20:
                display_name = display_name[:20] + "..."

            text = f"Hello, {display_name}"

            name_font = _get_start_font(
                max(20, scx(31))
            )

            # Text position
            text_x = scx(1005)
            text_y = scy(386)

            # Text shadow
            draw.text(
                (text_x + scx(2), text_y + scy(2)),
                text,
                font=name_font,
                fill=(0, 0, 0, 190)
            )

            # Main text
            draw.text(
                (text_x, text_y),
                text,
                font=name_font,
                fill=(245, 235, 255, 255),
                stroke_width=max(1, scx(1)),
                stroke_fill=(25, 5, 45, 230)
            )

            # ------------------------------------------------
            # SAVE GENERATED IMAGE
            # ------------------------------------------------

            filename = (
                f"start_user_"
                f"{int(time.time() * 1000000)}_"
                f"{random.randint(1000, 9999)}.png"
            )

            output = os.path.join(
                START_IMAGE_CACHE_DIR,
                filename
            )

            img.save(
                output,
                "PNG",
                optimize=True
            )

            return output

        return await asyncio.to_thread(_create)

    except Exception as e:
        print(f"[START IMAGE CREATE ERROR] {e}")
        return None


# ============================================================
# SUPPORT / UPDATE BUTTON
# ============================================================

def _msb():
    global _SB

    if _SB:
        return _SB

    sc = (
        SUPPORT_CHAT.lstrip('@')
        if not SUPPORT_CHAT.startswith("http")
        else SUPPORT_CHAT
    )

    uc = (
        UPDATE_CHANNEL.lstrip('@')
        if not UPDATE_CHANNEL.startswith("http")
        else UPDATE_CHANNEL
    )

    su = (
        sc
        if sc.startswith("http")
        else f"https://t.me/{sc}"
    )

    uu = (
        uc
        if uc.startswith("http")
        else f"https://t.me/{uc}"
    )

    _SB = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                font('Support'),
                url=su,
                style=ButtonStyle.PRIMARY
            )
        ],
        [
            InlineKeyboardButton(
                font('Updates'),
                url=uu,
                style=ButtonStyle.SUCCESS
            )
        ]
    ])

    return _SB


SB = _msb()


# ============================================================
# SMALL HELPERS
# ============================================================

def irc(cid):
    pass


def imc(cid, uid):
    pass


async def _st():
    global _tr, _bi

    if _tr:
        return

    _tr = True

    if not _bi:
        try:
            _bi = await pbot.get_me()
        except Exception as e:
            print(f"[ST ERROR] {e}")


def _gbi():
    return _bi


# ============================================================
# START BUTTONS
# ============================================================

def _gsb(uid):

    su = (
        SUPPORT_CHAT
        if SUPPORT_CHAT.startswith("http")
        else f"https://t.me/{SUPPORT_CHAT.lstrip('@')}"
    )

    uu = (
        UPDATE_CHANNEL
        if UPDATE_CHANNEL.startswith("http")
        else f"https://t.me/{UPDATE_CHANNEL.lstrip('@')}"
    )

    au = f"https://t.me/{BOT_UN}?startgroup=true"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                font("＋ 𝐈ηᴛᴇɢʀᴀᴛᴇ 𝐈η 𝐘ᴏᴜʀ 𝐂ʜᴀᴛ ＋"),
                url=au,
                style=ButtonStyle.SUCCESS
            )
        ],
        [
            InlineKeyboardButton(
                font("🎧 𝐌ᴜsɪᴄ"),
                url="https://t.me/AR_MUSIC_27BOT?start=help",
                style=ButtonStyle.PRIMARY
            ),
            InlineKeyboardButton(
                font("⚙ 𝐇ᴇʟᴘ ⚙"),
                callback_data=f"help_{uid}",
                style=ButtonStyle.DANGER
            )
        ],
        [
            InlineKeyboardButton(
                font("𝐔ᴘᴅᴀᴛᴇs ⎘"),
                url=uu,
                style=ButtonStyle.PRIMARY
            ),
            InlineKeyboardButton(
                font("𝐒ᴜᴘᴘᴏʀᴛ ☏︎"),
                url=su,
                style=ButtonStyle.PRIMARY
            )
        ],
        [
            InlineKeyboardButton(
                font("σᴡηᴇʀ ✧ ᴀʀ"),
                user_id=config.ALONE_OWNER_ID,
                style=ButtonStyle.SUCCESS
            )
        ]
    ])


# ============================================================
# SEND PHOTO
# ============================================================

async def _sp(cid, p, c=None, rm=None, eid=None, rt=None):

    try:

        if isinstance(p, (list, tuple)):
            p = p[0] if p else None

        if isinstance(c, (list, tuple)):
            c = c[0] if c else None

        if not p or not isinstance(p, str):

            if c:

                try:
                    return await pbot.send_message(
                        chat_id=cid,
                        text=c,
                        reply_markup=rm,
                        reply_to_message_id=rt,
                        effect_id=eid
                    )

                except Exception as e:
                    print(f"[SP MSG ERROR] {e}")

                    return await pbot.send_message(
                        chat_id=cid,
                        text=c
                    )

            return None

        kw = {
            'chat_id': cid,
            'photo': p,
            'caption': c,
            'reply_markup': rm
        }

        if rt:
            kw['reply_to_message_id'] = rt

        try:

            if eid:
                kw['message_effect_id'] = eid

            return await pbot.send_photo(**kw)

        except TypeError:

            try:

                kw.pop(
                    'message_effect_id',
                    None
                )

                kw['effect_id'] = eid

                return await pbot.send_photo(**kw)

            except:
                raise

    except FloodWait as e:

        print(f"[SP FLOODWAIT] {e}")

        await asyncio.sleep(
            min(
                10,
                getattr(e, "value", 1)
            )
        )

        return await _sp(
            cid,
            p,
            c,
            rm,
            eid,
            rt
        )

    except Exception as e:

        print(f"[SP ERROR] {e}")

        try:

            return await pbot.send_message(
                chat_id=cid,
                text=c or "❌ Photo failed to send.",
                reply_markup=rm
            )

        except Exception as e2:

            print(
                f"[SP FALLBACK ERROR] {e2}"
            )

            return None


# ============================================================
# SEND MESSAGE
# ============================================================

async def _sm(cid, t, rm=None, eid=None, rt=None):

    try:

        if isinstance(t, (list, tuple)):
            t = str(t[0]) if t else ""

        if not isinstance(t, str):
            t = str(t)

        if not t:
            return None

        kw = {
            'chat_id': cid,
            'text': t,
            'reply_markup': rm
        }

        if rt:
            kw['reply_to_message_id'] = rt

        if eid:

            try:

                kw['effect_id'] = eid

                return await pbot.send_message(
                    **kw
                )

            except TypeError:

                kw.pop(
                    'effect_id',
                    None
                )

                kw['message_effect_id'] = eid

                return await pbot.send_message(
                    **kw
                )

        return await pbot.send_message(
            **kw
        )

    except FloodWait as e:

        print(f"[SM FLOODWAIT] {e}")

        await asyncio.sleep(
            min(
                10,
                getattr(e, "value", 1)
            )
        )

        return await _sm(
            cid,
            t,
            rm,
            eid,
            rt
        )

    except Exception as e:

        print(f"[SM ERROR] {e}")

        try:

            return await pbot.send_message(
                chat_id=cid,
                text=t
            )

        except Exception as e2:

            print(
                f"[SM FALLBACK ERROR] {e2}"
            )

            return None


# ============================================================
# GET CHAT NAME
# ============================================================

async def _gcn(cid):

    try:

        ch = await pbot.get_chat(cid)

        return getattr(
            ch,
            "title",
            "this chat"
        )

    except Exception as e:

        print(f"[GCN ERROR] {e}")

        return "this chat"


# ============================================================
# CHECK MEMBERSHIP
# ============================================================

async def _cm(cid, uid):

    try:
        return await check_membership(
            cid,
            uid
        )

    except Exception as e:

        print(f"[CM ERROR] {e}")

        return False


# ============================================================
# BASE64
# ============================================================

def _db64(p):

    try:

        return base64.b64decode(
            p.encode()
        ).decode()

    except Exception as e:

        print(f"[DB64 ERROR] {e}")

        return None


# ============================================================
# AUTO FILTER HANDLER
# ============================================================

async def _haf(uid, t, p):

    try:

        d = decode_to_base64(
            p.encode()
        )

        au, _, idx = d.partition("&")

        idx = (
            int(idx)
            if idx.isdigit()
            else None
        )

        m = await _cm(
            config.AF_SUB_CHAT,
            uid
        )

        if m:

            if not idx:

                await _sm(
                    uid,
                    "❌ Invalid file reference."
                )

                return True

            f = await get_file_by_index(
                idx
            )

            await autofilter_send_file(
                pbot,
                t,
                uid,
                f
            )

            return True

        cu = (
            f"https://t.me/"
            f"{config.AF_SUB_CHAT.lstrip('@')}"
        )

        bs = (
            f"t.me/{BOT_UN}"
            f"?start={t}"
        )

        b = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    font(
                        '📢 My ( Channel / Group )'
                    ),
                    url=cu,
                    style=ButtonStyle.PRIMARY
                )
            ],
            [
                InlineKeyboardButton(
                    font('📁 Get File'),
                    url=bs,
                    style=ButtonStyle.SUCCESS
                )
            ]
        ])

        await _sp(
            uid,
            config.FORCE_JOIN_IMG,
            config.AF_SUB_TEXT,
            b,
            random.choice(SE)
        )

        return True

    except Exception as e:

        print(f"[HAF ERROR] {e}")

        return False


# ============================================================
# GET MEDIA
# ============================================================

async def _hgm(uid, p):

    try:

        d = _db64(p)

        if not d:

            await _sm(
                uid,
                "❌ Invalid media payload."
            )

            return True

        mt, _, m = d.partition("&")

        mm = {
            "photo": pbot.send_photo,
            "video": pbot.send_video,
            "animation": pbot.send_animation,
            "audio": pbot.send_audio
        }

        me = mm.get(mt)

        if me:
            await me(uid, m)

        else:
            await _sm(
                uid,
                "❌ Unsupported media type."
            )

        return True

    except Exception as e:

        print(f"[HGM ERROR] {e}")

        return False


# ============================================================
# GET FILE
# ============================================================

async def _hgf(uid, t, p):

    try:

        d = _db64(p)

        if not d:

            await _sm(
                uid,
                "❌ Invalid file payload."
            )

            return True

        ms, _, uq = d.partition("&")

        if not ms.isdigit():

            await _sm(
                uid,
                "**This file is removed or an invalid link!** 👻"
            )

            return True

        mid = int(ms)

        fm = await pbot.get_messages(
            config.FILE_DB_CHANNEL,
            mid
        )

        if not fm:

            await _sm(
                uid,
                "**This file is removed or an invalid link!** 👻"
            )

            return True

        fuid = None

        for at in (
            "document",
            "video",
            "sticker",
            "photo",
            "animation",
            "audio"
        ):

            it = getattr(
                fm,
                at,
                None
            )

            if it:

                obj = (
                    it[-1]
                    if at == "photo"
                    and isinstance(it, list)
                    else it
                )

                fuid = getattr(
                    obj,
                    "file_unique_id",
                    None
                )

                if fuid:
                    break

        if uq != fuid:

            await _sm(
                uid,
                "**This is not a valid link!** 🤨"
            )

            return True

        m = await _cm(
            config.UPDATE_CHANNEL,
            uid
        )

        if not m:

            b = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        font("⚡ Channel"),
                        url=(
                            f"t.me/"
                            f"{config.UPDATE_CHANNEL.lstrip('@')}"
                        ),
                        style=ButtonStyle.PRIMARY
                    )
                ],
                [
                    InlineKeyboardButton(
                        font("⚡ Try again"),
                        url=(
                            f"t.me/{BOT_UN}"
                            f"?start={t}"
                        ),
                        style=ButtonStyle.SUCCESS
                    )
                ]
            ])

            await _sm(
                uid,
                "**In order to access file please Join my channel!**",
                b
            )

            return True

        fw = await fm.forward(uid)

        aft = getattr(
            config,
            "AF_FILE_DEL_TIME",
            60
        )

        await fw.reply_text(
            f"✨ **Thank you for using me!**\n"
            f"```\n"
            f"The file will be deleted after "
            f"{time_formatter(aft)}, so please save it "
            f"somewhere else like Saved Messages!"
            f"```"
        )

        asyncio.create_task(
            auto_delete(
                fw,
                aft
            )
        )

        return True

    except Exception as e:

        print(f"[HGF ERROR] {e}")

        return False


# ============================================================
# RULES
# ============================================================

async def _hr(uid, cid):

    try:

        ci = int(cid)

        rt = (
            await get_rules(ci)
            or DEFAULT_MESSAGE
        )

        cn = await _gcn(ci)

        await _sm(
            uid,
            f"📜 **Rules for {cn}:**\n\n{rt}",
            None,
            random.choice(SE)
        )

        return True

    except Exception as e:

        print(f"[HR ERROR] {e}")

        await _sm(
            uid,
            "❌ Invalid chat rules link."
        )

        return False


# ============================================================
# HELP DEEPLINK
# ============================================================

async def _hh(uid, msg, u):

    try:

        b = await get_help_button(
            msg,
            u
        )

        if not b:

            await _sm(
                uid,
                "Help menu not available."
            )

            return False

        hc = (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote><b>"
            f"{font('Hii')} {u.mention}!\n\n"
            f"{font('Need help or want to support us?')}\n\n"
            f"{font('Main available commands:')}\n"
            f"- /support : "
            f"{font('Connect with our support.')}\n"
            f"- /alive : "
            f"{font('Check uptime')}\n"
            f"- /donate : "
            f"{font('For information about donations!')}\n"
            f"- /privacy : "
            f"{font('Learn how we protect your privacy.')}\n"
            f"- {font('In a group: Get your group settings.')}"
            f"</b></blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )

        await _sp(
            uid,
            config.HELP_CMD_IMG,
            hc,
            b,
            random.choice(SE)
        )

        return True

    except Exception as e:

        print(f"[HH ERROR] {e}")

        await _sm(
            uid,
            "Error loading help menu."
        )

        return False


# ============================================================
# DEEPLINK
# ============================================================

async def _dl(msg):

    a = msg.text.split(
        None,
        1
    )

    if len(a) < 2:
        return False

    t = a[1]

    uid = msg.from_user.id

    try:

        if t.startswith('manage_'):
            return await handle_admin_deeplink(
                msg,
                t
            )

        if t.startswith('settings_'):
            return await handle_settings_deeplink(
                msg,
                t
            )

        if t.startswith('afFile'):

            _, _, p = t.partition('-')

            return (
                await _haf(
                    uid,
                    t,
                    p
                )
                if p
                else False
            )

        if t.startswith(
            ('music', 'sud', 'inf')
        ):
            return True

        if t.startswith("getmedia"):

            _, _, p = t.partition('-')

            return (
                await _hgm(
                    uid,
                    p
                )
                if p
                else False
            )

        if t.startswith("getfile"):

            _, _, p = t.partition('-')

            return (
                await _hgf(
                    uid,
                    t,
                    p
                )
                if p
                else False
            )

        if t.startswith("rules_"):

            _, _, c = t.partition("_")

            return await _hr(
                uid,
                c
            )

        if t.startswith('help'):

            return await _hh(
                uid,
                msg,
                msg.from_user
            )

        await _sm(
            uid,
            "**No deep message detected for this link 🤷**"
        )

        return False

    except Exception as e:

        print(f"[DL ERROR] {e}")

        await _sm(
            uid,
            "❌ Error processing request"
        )

        return False


# ============================================================
# START LOG
# ============================================================

async def _bst(uid, u, cmd):

    try:

        us = await get_user_join_source(uid)

        w = datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S'
        )

        un = (
            f"@{u.username}"
            if u.username
            else "No Username"
        )

        if us == 'new':

            lt = (
                f"⚡ **New User Started Bot**\n\n"
                f"**👤 User:** {u.mention}\n"
                f"**🆔 ID:** `{uid}`\n"
                f"**🔗 Username:** {un}\n"
                f"**📍 Source:** Direct DM\n"
                f"**🔧 Command:** `/{cmd}`\n"
                f"**📅 Date:** `{w}`"
            )

        elif us == 'group_inactive':

            lt = (
                f"⚡ **New Active User**\n\n"
                f"**👤 User:** {u.mention}\n"
                f"**🆔 ID:** `{uid}`\n"
                f"**🔗 Username:** {un}\n"
                f"**📍 Source:** Group → DM\n"
                f"**🔧 Command:** `/{cmd}`\n"
                f"**📅 Date:** `{w}`"
            )

        else:

            lt = (
                f"⚡ **User Started Bot**\n\n"
                f"**👤 User:** {u.mention}\n"
                f"**🆔 ID:** `{uid}`\n"
                f"**🔗 Username:** {un}\n"
                f"**📍 Source:** Returning User\n"
                f"**🔧 Command:** `/{cmd}`\n"
                f"**📅 Date:** `{w}`"
            )

        if LOGS_CHANNEL:

            asyncio.create_task(
                pbot.send_message(
                    LOGS_CHANNEL,
                    lt
                )
            )

    except Exception as e:

        print(f"[BST ERROR] {e}")


# ============================================================
# GROUP START LOG
# ============================================================

async def _bst_group(chat, u, cmd):

    try:

        w = datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S'
        )

        un = (
            f"@{u.username}"
            if u.username
            else "No Username"
        )

        lt = (
            f"⚡ **Bot Started in Group**\n\n"
            f"**👥 Group:** {chat.title}\n"
            f"**🆔 Chat ID:** `{chat.id}`\n"
            f"**👤 Started By:** {u.mention}\n"
            f"**🆔 User ID:** `{u.id}`\n"
            f"**🔗 Username:** {un}\n"
            f"**🔧 Command:** `/{cmd}`\n"
            f"**📅 Date:** `{w}`"
        )

        if LOGS_CHANNEL:

            asyncio.create_task(
                pbot.send_message(
                    LOGS_CHANNEL,
                    lt
                )
            )

    except Exception as e:

        print(
            f"[BST_GROUP ERROR] {e}"
        )


# ============================================================
# START QUEUE
# ============================================================

async def _process_start_queue():

    while True:

        try:

            msg = await _user_queue.get()

            if msg is None:
                break

            uid = msg.from_user.id

            if uid in _processing_users:

                _user_queue.task_done()

                continue

            ct = time.time()

            lpt = _last_process_time.get(
                uid,
                0
            )

            if ct - lpt < 2:

                await asyncio.sleep(
                    2 - (ct - lpt)
                )

            _processing_users.add(uid)

            async with _semaphore:

                try:

                    await _handle_start_private(
                        msg
                    )

                except Exception as e:

                    print(
                        f"[QUEUE PROCESS ERROR] {e}"
                    )

                finally:

                    _last_process_time[uid] = time.time()

                    await asyncio.sleep(
                        0.1
                    )

            _processing_users.discard(uid)

            _user_queue.task_done()

        except Exception as e:

            print(
                f"[QUEUE ERROR] {e}"
            )

            await asyncio.sleep(1)


# ============================================================
# QUEUE START
# ============================================================

async def _ensure_queue_processor():

    global _queue_processor_started

    if not _queue_processor_started:

        _queue_processor_started = True

        asyncio.create_task(
            _process_start_queue()
        )


# ============================================================
# PRIVATE START
# ============================================================

async def _handle_start_private(message: Message):

    try:

        u = message.from_user

        if not u:
            return

        # ----------------------------------------------------
        # DEEPLINK
        # ----------------------------------------------------

        if (
            message.text
            and len(message.text.split()) > 1
        ):

            if await _dl(message):
                return

        uid = u.id

        ct = time.time()

        is_cached = (
            'start' in _cmd_cache[uid]
            and
            (
                ct -
                _cmd_cache[uid]['start']
            ) < _cache_expiry
        )

        if not is_cached:

            _cmd_cache[uid]['start'] = ct

            join_source = await get_user_join_source(
                uid
            )

            asyncio.create_task(
                _bst(
                    uid,
                    u,
                    'start'
                )
            )

            asyncio.create_task(
                add_user({
                    'id': uid,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'username': u.username,
                    'is_bot': u.is_bot
                })
            )

            if join_source in [
                'new',
                'group_inactive'
            ]:

                asyncio.create_task(
                    activate_user(uid)
                )

        # ----------------------------------------------------
        # BOT INFO
        # ----------------------------------------------------

        bi = _gbi()

        bm = (
            f"[{bi.first_name}]"
            f"(tg://user?id={bi.id})"
            if bi
            else "I"
        )

        # ----------------------------------------------------
        # BUTTONS
        # ----------------------------------------------------

        b = _gsb(uid)

        # ----------------------------------------------------
        # START CAPTION
        # ----------------------------------------------------

        tx = (
            f"<blockquote><b>"
            f"⍣ 𝖧𝖾𝗒𝖺 {u.mention} {bm} "
            f"𝖨'𝗆 𝖠𝗇 𝖠𝖽𝗏𝖺𝗇𝖼𝖾 𝖠𝖨 "
            f"𝖨𝗇𝗍𝖾𝗀𝗋𝖺𝗍𝖾𝖽 𝖱𝗈𝖻𝗈𝗍, "
            f"𝖨'𝗅𝗅 𝖬𝖺𝗇𝖺𝗀𝖾 "
            f"𝖸𝗈𝗎𝗋 𝖦𝗋𝗈𝗎𝗉 "
            f"𝖤𝖺𝗌𝗂𝗅𝗒."
            f"</b></blockquote>\n"
            f"──────────────────────\n"
            f"<blockquote><b>"
            f"➛ 70+ 𝖬𝗎𝗅𝗍𝗂𝗉𝗅𝖾 "
            f"𝖥𝖾𝖺𝗍𝗎𝗋𝖾𝗌 𝖶𝗂𝗍𝗁 𝖠𝗂\n"
            f"➛ E𝖺𝗌𝗒 𝖳𝗈 𝖴𝗌𝖾, "
            f"𝖠𝗅𝗅 𝖨𝗇 𝖮𝗇𝖾 𝖡𝗈𝗍\n"
            f"➛ 𝖲𝖺𝖿𝖾𝗌𝗍 "
            f"𝖦𝗋𝗈𝗎𝗉 𝖬𝖺𝗇𝖺𝗀𝖾𝗆𝖾𝗇𝗍 "
            f"𝖡𝗈𝗍"
            f"</b></blockquote>\n"
            f"──────────────────────\n"
            f"<blockquote><b>"
            f"⍣ 𝖧𝗂𝗍 𝖳𝗁𝖾 "
            f"/help 𝖡𝗎𝗍𝗍𝗈𝗇 𝖳𝗈 "
            f"𝖪𝗇𝗈𝗐 𝖬𝗒 "
            f"𝖠𝖻𝗂𝗅𝗂𝗍𝗂𝖾𝗌"
            f"</b></blockquote>"
        )

        # ----------------------------------------------------
        # CREATE DYNAMIC START IMAGE
        # ----------------------------------------------------

        start_image = await _make_start_image(
            u.first_name or "User"
        )

        # ----------------------------------------------------
        # SEND DYNAMIC IMAGE
        # ----------------------------------------------------

        if start_image:

            try:

                await _sp(
                    cid=message.chat.id,
                    p=start_image,
                    c=tx,
                    rm=b,
                    eid=random.choice(SE)
                )

            finally:

                try:

                    if os.path.exists(
                        start_image
                    ):

                        os.remove(
                            start_image
                        )

                except Exception:
                    pass

        else:

            # ------------------------------------------------
            # IMAGE CREATE FAIL HO TO ORIGINAL URL SEND
            # ------------------------------------------------

            await _sp(
                cid=message.chat.id,
                p=getattr(
                    config,
                    "START_IMG_URL",
                    None
                ),
                c=tx,
                rm=b,
                eid=random.choice(SE)
            )

    except Exception as e:

        print(
            f"[HANDLE_START_PRIVATE ERROR] {e}"
        )

        try:

            await _sm(
                message.chat.id,
                "Hello — something went wrong while showing start. Check logs."
            )

        except Exception as e2:

            print(
                f"[HANDLE_START_PRIVATE FALLBACK ERROR] {e2}"
            )


# ============================================================
# PRIVATE START COMMAND
# ============================================================

@pbot.on_message(
    filters.command(
        'start',
        prefixes=prefix_cmds
    )
    & filters.private,
    group=11
)
async def start_private(
    client: Client,
    message: Message
):

    try:

        asyncio.create_task(
            _st()
        )

        await _ensure_queue_processor()

        await _user_queue.put(
            message
        )

    except Exception as e:

        print(
            f"[START_PRIVATE ERROR] {e}"
        )

        try:

            await _sm(
                message.chat.id,
                "Please try again in a moment."
            )

        except Exception as e2:

            print(
                f"[START_PRIVATE FALLBACK ERROR] {e2}"
            )


# ============================================================
# GROUP START
# ============================================================

@pbot.on_message(
    filters.command(
        'start',
        prefixes=prefix_cmds
    )
    & filters.group,
    group=12
)
async def start_group(
    client: Client,
    message: Message
):

    try:

        asyncio.create_task(
            _st()
        )

        asyncio.create_task(
            check_chat_exists(
                message.chat.id
            )
        )

        asyncio.create_task(
            _bst_group(
                message.chat,
                message.from_user,
                'start'
            )
        )

        await _sp(
            cid=message.chat.id,
            p=getattr(
                config,
                "START_IMG",
                None
            ),
            c=(
                "👋 Hello everyone! Rosie here.\n"
                "I'm ready to manage and protect "
                "this group. Type /help to see "
                "what I can do!"
            )
        )

    except Exception as e:

        print(
            f"[START_GROUP ERROR] {e}"
        )


# ============================================================
# PRIVATE HELP
# ============================================================

@pbot.on_message(
    filters.command(
        'help',
        prefixes=prefix_cmds
    )
    & filters.private,
    group=13
)
async def help_private(
    client: Client,
    message: Message
):

    try:

        u = message.from_user

        if not u:
            return

        uid = u.id

        ct = time.time()

        t = message.text or ""

        p = t.split(
            maxsplit=1
        )

        if len(p) == 2:

            hm = p[1].strip().lower()

            if hm in MODULE:

                r = message.reply_to_message

                await _sp(
                    cid=message.chat.id,
                    p=getattr(
                        config,
                        "HELP_MODULE_IMG",
                        None
                    ),
                    c=MODULE[hm],
                    rm=None,
                    eid=random.choice(SE),
                    rt=(
                        r.id
                        if r
                        else message.id
                    )
                )

                return

        is_cached = (
            'help' in _cmd_cache[uid]
            and
            (
                ct -
                _cmd_cache[uid]['help']
            ) < _cache_expiry
        )

        if not is_cached:

            _cmd_cache[uid]['help'] = ct

            join_source = (
                await get_user_join_source(
                    uid
                )
            )

            asyncio.create_task(
                _bst(
                    uid,
                    u,
                    'help'
                )
            )

            asyncio.create_task(
                add_user({
                    'id': uid,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'username': u.username,
                    'is_bot': u.is_bot
                })
            )

            if join_source in [
                'new',
                'group_inactive'
            ]:

                asyncio.create_task(
                    activate_user(uid)
                )

        b = await get_help_button(
            message,
            u
        )

        if not b:

            await _sm(
                message.chat.id,
                "Help buttons not available."
            )

            return

        ht = (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote><b>"
            f"{font('Hii')} {u.mention}!\n\n"
            f"{font('Need help or want to support us?')}\n\n"
            f"{font('Main available commands:')}\n"
            f"- /support : "
            f"{font('Connect with our support.')}\n"
            f"- /alive : "
            f"{font('Check uptime')}\n"
            f"- /donate : "
            f"{font('For information about donations!')}\n"
            f"- /privacy : "
            f"{font('Learn how we protect your privacy.')}\n"
            f"- {font('In a group: Get your group settings.')}"
            f"</b></blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )

        await _sp(
            cid=message.chat.id,
            p=getattr(
                config,
                "HELP_CMD_IMG",
                None
            ),
            c=ht,
            rm=b,
            eid=random.choice(SE)
        )

    except Exception as e:

        print(
            f"[HELP_PRIVATE ERROR] {e}"
        )

        await _sm(
            message.chat.id,
            "Error loading help menu."
        )


# ============================================================
# GROUP HELP
# ============================================================

@pbot.on_message(
    filters.command(
        'help',
        prefixes=prefix_cmds
    )
    & filters.group,
    group=14
)
@no_channel
async def help_group(
    client: Client,
    message: Message
):

    try:

        if (
            message.from_user
            and message.from_user.is_bot
        ):
            return

        await message.reply_text(
            font(
                "🧏 Check my all commands in private chat!"
            ),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        font("🆘 Commands"),
                        url=(
                            f"t.me/{BOT_UN}"
                            f"?start=help"
                        ),
                        style=ButtonStyle.SUCCESS
                    )
                ]
            ])
        )

    except Exception as e:

        print(
            f"[HELP_GROUP ERROR] {e}"
        )


# ============================================================
# PRIVACY / DONATE / SUPPORT
# ============================================================

PT = (
    "🗨️ **Privacy Policy:**\n\n"
    "We care about your privacy.\n\n"
    "📥 **Data Collection:** "
    "We only collect your unique Telegram User ID, "
    "necessary for our bot to function properly.\n\n"
    "🔎 **Data Use:** "
    "We don't share your User ID with third-party "
    "apps or services. Data is only used to support "
    "bot features such as preferences, command usage, "
    "and permission checks.\n\n"
    "🧾 **Logs & Storage:** "
    "We may store minimal logs (timestamps and user IDs) "
    "for moderation and abuse prevention. Files you upload "
    "are not shared and can be deleted on request.\n\n"
    "🙋 **Your Rights:** "
    "You have the right to request access, correction, "
    "or deletion of your data. To request this, contact "
    "the support chat below or use bot commands if available.\n\n"
    "🔒 **Security:** "
    "We take reasonable measures to protect data, but no "
    "system is 100% secure. Please avoid sending sensitive "
    "personal information.\n\n"
    "🤷 **Changes to this Policy:** "
    "We may update this policy. By using our bot, you agree "
    "to this policy. If major changes are made, we will "
    "notify users in the update channel."
)


DT = (
    f"🙏 **Thank you for considering donating to help "
    f"keep this Bot alive and functioning!**\n\n"
    f"⚫ You can also donate telegram stars using "
    f"/pay command.\n\n"
    f"🙋 Please reach out at {SUPPORT_CHAT}."
)


ST = (
    f"👮 **Click below buttons to reach out to the official "
    f"Support for** {BOT_USERNAME}**.**"
)


# ============================================================
# SUPPORT
# ============================================================

@pbot.on_message(
    filters.command(
        'support',
        prefixes=prefix_cmds
    )
    & filters.private,
    group=-310
)
@no_channel
async def support_cmd(
    client: Client,
    message: Message
):

    try:

        u = message.from_user

        if not u:
            return

        uid = u.id

        ct = time.time()

        is_cached = (
            'support' in _cmd_cache[uid]
            and
            (
                ct -
                _cmd_cache[uid]['support']
            ) < _cache_expiry
        )

        if not is_cached:

            _cmd_cache[uid]['support'] = ct

            join_source = (
                await get_user_join_source(
                    uid
                )
            )

            asyncio.create_task(
                _bst(
                    uid,
                    u,
                    'support'
                )
            )

            asyncio.create_task(
                add_user({
                    'id': uid,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'username': u.username,
                    'is_bot': u.is_bot
                })
            )

            if join_source in [
                'new',
                'group_inactive'
            ]:

                asyncio.create_task(
                    activate_user(uid)
                )

        await _sm(
            message.chat.id,
            ST,
            SB,
            random.choice(SE)
        )

    except Exception as e:

        print(
            f"[SUPPORT_CMD ERROR] {e}"
        )


# ============================================================
# DONATE
# ============================================================

@pbot.on_message(
    filters.command(
        'donate',
        prefixes=prefix_cmds
    )
    & filters.private,
    group=15
)
@no_channel
async def donate_cmd(
    client: Client,
    message: Message
):

    try:

        u = message.from_user

        if not u:
            return

        uid = u.id

        ct = time.time()

        is_cached = (
            'donate' in _cmd_cache[uid]
            and
            (
                ct -
                _cmd_cache[uid]['donate']
            ) < _cache_expiry
        )

        if not is_cached:

            _cmd_cache[uid]['donate'] = ct

            join_source = (
                await get_user_join_source(
                    uid
                )
            )

            asyncio.create_task(
                _bst(
                    uid,
                    u,
                    'donate'
                )
            )

            asyncio.create_task(
                add_user({
                    'id': uid,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'username': u.username,
                    'is_bot': u.is_bot
                })
            )

            if join_source in [
                'new',
                'group_inactive'
            ]:

                asyncio.create_task(
                    activate_user(uid)
                )

        await _sm(
            message.chat.id,
            DT,
            None,
            random.choice(SE)
        )

    except Exception as e:

        print(
            f"[DONATE_CMD ERROR] {e}"
        )


# ============================================================
# PRIVACY
# ============================================================

@pbot.on_message(
    filters.command(
        'privacy',
        prefixes=prefix_cmds
    )
    & filters.private,
    group=16
)
@no_channel
async def privacy_cmd(
    client: Client,
    message: Message
):

    try:

        u = message.from_user

        if not u:
            return

        uid = u.id

        ct = time.time()

        is_cached = (
            'privacy' in _cmd_cache[uid]
            and
            (
                ct -
                _cmd_cache[uid]['privacy']
            ) < _cache_expiry
        )

        if not is_cached:

            _cmd_cache[uid]['privacy'] = ct

            join_source = (
                await get_user_join_source(
                    uid
                )
            )

            asyncio.create_task(
                _bst(
                    uid,
                    u,
                    'privacy'
                )
            )

            asyncio.create_task(
                add_user({
                    'id': uid,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'username': u.username,
                    'is_bot': u.is_bot
                })
            )

            if join_source in [
                'new',
                'group_inactive'
            ]:

                asyncio.create_task(
                    activate_user(uid)
                )

        await _sm(
            message.chat.id,
            PT,
            None,
            random.choice(SE)
        )

    except Exception as e:

        print(
            f"[PRIVACY_CMD ERROR] {e}"
                )
