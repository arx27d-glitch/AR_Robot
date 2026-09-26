# ============================================================
#                    AR WORLD GAME BOT
#                  COMPLETE GAME.PY
# ============================================================

import random
from datetime import datetime, timedelta

from pyrogram import filters, types
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from AloneX import pbot as bot

from AloneX.db.game import (
    register_user,
    get_cash,
    update_cash,
    update_name,
    update_kills,
    get_kills,
    set_protection,
    get_protection,
    get_profile,
    get_richlist,
    add_bank,
    remove_bank,
    get_bank,
    update_bank,
    add_item,
    remove_item,
    get_inventory,
    has_item,
)


# ============================================================
# GLOBAL DATA
# ============================================================

xo_games = {}
xo_invites = {}

arworld_cd = {}

game_cooldowns = {
    "daily": {},
    "work": {},
    "beg": {},
    "bonus": {},
    "mine": {},
    "fish": {},
    "hunt": {},
    "flip": {},
    "crime": {},
    "rob": {},
}

COOLDOWN_TIME = {
    "daily": 86400,
    "work": 3600,
    "beg": 300,
    "bonus": 43200,
    "mine": 180,
    "fish": 180,
    "hunt": 300,
    "flip": 10,
    "crime": 120,
    "rob": 180,
}


# ============================================================
# COMMON HELPERS
# ============================================================

def close_button(user_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "❌ Close",
                    callback_data=f"close_{user_id}",
                )
            ]
        ]
    )


async def delete_command(message):
    try:
        await message.delete()
    except Exception:
        pass


async def ensure_user(user):
    try:
        await register_user(user.id)
    except Exception:
        pass

    try:
        await update_name(
            user.id,
            user.first_name or "Unknown",
        )
    except Exception:
        pass


def parse_amount(value):
    try:
        amount = int(value)

        if amount <= 0:
            return None

        return amount

    except Exception:
        return None


def now_ts():
    return datetime.now().timestamp()


def cooldown_left(command, user_id):
    last = game_cooldowns.get(command, {}).get(user_id)

    if not last:
        return 0

    remaining = COOLDOWN_TIME[command] - (
        now_ts() - last
    )

    if remaining <= 0:
        return 0

    return int(remaining)


def set_cooldown(command, user_id):
    if command not in game_cooldowns:
        game_cooldowns[command] = {}

    game_cooldowns[command][user_id] = now_ts()


def format_time(seconds):
    seconds = int(seconds)

    if seconds <= 0:
        return "Ready"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours:
        return f"{hours}h {minutes}m"

    if minutes:
        return f"{minutes}m {secs}s"

    return f"{secs}s"


def money(amount):
    return f"₹{int(amount):,}"


# ============================================================
# AR WORLD
# ============================================================

ARWORLD_EVENTS = [
    {
        "text": "💎 You discovered a hidden treasure!",
        "min": 1000,
        "max": 5000,
    },
    {
        "text": "🪙 You found an old coin collection!",
        "min": 500,
        "max": 2500,
    },
    {
        "text": "🏆 You completed a secret mission!",
        "min": 1500,
        "max": 6000,
    },
    {
        "text": "📦 You found a mysterious package!",
        "min": 300,
        "max": 2000,
    },
    {
        "text": "💼 A stranger hired you for a quick job!",
        "min": 700,
        "max": 3500,
    },
    {
        "text": "🌟 You discovered a rare artifact!",
        "min": 2000,
        "max": 8000,
    },
    {
        "text": "🕳️ You found an underground stash!",
        "min": 800,
        "max": 4000,
    },
    {
        "text": "🎁 Someone left a gift for you!",
        "min": 400,
        "max": 3000,
    },
]


@bot.on_message(filters.command("arworld"))
async def arworld(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    current = now_ts()
    last = arworld_cd.get(uid, 0)

    if current - last < 30:
        remaining = int(30 - (current - last))

        return await m.reply_text(
            f"""
╭━━━〔 🌎 AR WORLD 〕━━━╮
│
│ ⏳ **World is recharging!**
│
│ Try again in:
│ `{remaining}s`
│
╰━━━━━━━━━━━━━━━━━━━━╯
""",
            reply_markup=close_button(uid),
        )

    arworld_cd[uid] = current

    event = random.choice(ARWORLD_EVENTS)

    reward = random.randint(
        event["min"],
        event["max"],
    )

    bonus_text = ""

    # 10% bonus
    if random.randint(1, 100) <= 10:
        bonus = random.randint(3000, 7000)
        reward += bonus

        bonus_text = (
            f"\n│ 🔥 Lucky Bonus: **+{money(bonus)}**\n"
        )

    # 1% jackpot
    if random.randint(1, 100) == 1:
        jackpot = random.randint(15000, 50000)
        reward += jackpot

        bonus_text += (
            f"\n│ 💎 JACKPOT: **+{money(jackpot)}**\n"
        )

    update_cash(uid, reward)

    locations = [
        "🏙️ Neon City",
        "🌲 Dark Forest",
        "🏜️ Lost Desert",
        "🏝️ Mystery Island",
        "🏰 Ancient Castle",
        "🌌 Shadow Valley",
        "⛰️ Crystal Mountain",
    ]

    location = random.choice(locations)

    return await m.reply_text(
        f"""
╭━━━〔 🌎 AR WORLD 〕━━━╮
│
│ 📍 Location:
│ **{location}**
│
│ {event["text"]}
│
│ 💰 Reward:
│ **+{money(reward)}**
{bonus_text}│
│ 🎒 Adventure completed!
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# BALANCE
# ============================================================

@bot.on_message(filters.command(["bal", "balance"]))
async def balance(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id
    cash = get_cash(uid)

    return await m.reply_text(
        f"""
╭━━━〔 💰 BALANCE 〕━━━╮
│
│ 👤 Player:
│ **{m.from_user.first_name}**
│
│ 💵 Cash:
│ **{money(cash)}**
│
│ 🏦 Bank:
│ **{money(get_bank(uid))}**
│
│ 💎 Total:
│ **{money(cash + get_bank(uid))}**
│
╰━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# DAILY
# ============================================================

@bot.on_message(filters.command("daily"))
async def daily(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    remaining = cooldown_left("daily", uid)

    if remaining:
        return await m.reply_text(
            f"""
╭━━━〔 🎁 DAILY 〕━━━╮
│
│ ❌ Already claimed!
│
│ ⏳ Come back in:
│ `{format_time(remaining)}`
│
╰━━━━━━━━━━━━━━━━━━━╯
""",
            reply_markup=close_button(uid),
        )

    reward = random.randint(1000, 5000)
    title = "🎁 DAILY REWARD"

    if random.randint(1, 100) <= 5:
        bonus = random.randint(5000, 15000)
        reward += bonus
        title = "💎 DAILY JACKPOT"

    update_cash(uid, reward)
    set_cooldown("daily", uid)

    return await m.reply_text(
        f"""
╭━━━〔 {title} 〕━━━╮
│
│ 👤 {m.from_user.first_name}
│
│ 💰 Received:
│ **+{money(reward)}**
│
│ 🔥 Come back tomorrow!
│
╰━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# WORK
# ============================================================

@bot.on_message(filters.command("work"))
async def work(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    remaining = cooldown_left("work", uid)

    if remaining:
        return await m.reply_text(
            f"""
╭━━━〔 💼 WORK 〕━━━╮
│
│ 😴 You're tired!
│
│ ⏳ Try again in:
│ `{format_time(remaining)}`
│
╰━━━━━━━━━━━━━━━━━━╯
""",
            reply_markup=close_button(uid),
        )

    jobs = [
        ("💻 Developer", 500, 2500),
        ("🎨 Designer", 400, 2200),
        ("📦 Delivery", 300, 1800),
        ("🧑‍🍳 Chef", 350, 2000),
        ("🛒 Shopkeeper", 450, 2300),
        ("🚗 Driver", 500, 2500),
    ]

    job, low, high = random.choice(jobs)
    reward = random.randint(low, high)

    update_cash(uid, reward)
    set_cooldown("work", uid)

    return await m.reply_text(
        f"""
╭━━━〔 💼 WORK COMPLETE 〕━━━╮
│
│ 🧑‍💼 Job:
│ **{job}**
│
│ 💰 Earned:
│ **+{money(reward)}**
│
│ ⚡ Hard work pays!
│
╰━━━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# CRIME
# ============================================================

CRIME_EVENTS = [
    (
        "🏪 You successfully robbed a small shop!",
        500,
        2500,
    ),
    (
        "💎 You found valuable loot during the mission!",
        1000,
        4000,
    ),
    (
        "🚗 You completed a risky delivery!",
        700,
        3000,
    ),
    (
        "🏦 You escaped with a small amount of loot!",
        1500,
        5000,
    ),
]


@bot.on_message(filters.command("crime"))
async def crime(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    remaining = cooldown_left("crime", uid)

    if remaining:
        return await m.reply_text(
            f"""
🚨 **Crime system cooling down**

⏳ Try again in:
`{format_time(remaining)}`
""",
            reply_markup=close_button(uid),
        )

    set_cooldown("crime", uid)

    if random.randint(1, 100) <= 65:
        event, low, high = random.choice(CRIME_EVENTS)
        reward = random.randint(low, high)

        update_cash(uid, reward)

        return await m.reply_text(
            f"""
╭━━━〔 🚨 CRIME SUCCESS 〕━━━╮
│
│ {event}
│
│ 💰 Loot:
│ **+{money(reward)}**
│
│ 🏃 You escaped successfully!
│
╰━━━━━━━━━━━━━━━━━━━━━━━━╯
""",
            reply_markup=close_button(uid),
        )

    fine = random.randint(200, 1200)
    cash = get_cash(uid)
    fine = min(fine, cash)

    update_cash(uid, -fine)

    return await m.reply_text(
        f"""
╭━━━〔 🚔 CRIME FAILED 〕━━━╮
│
│ ❌ You got caught!
│
│ 💸 Fine:
│ **-{money(fine)}**
│
│ Better luck next time.
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# GIVE
# ============================================================

@bot.on_message(filters.command("give"))
async def give(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    if not m.reply_to_message:
        return await m.reply_text(
            "❌ **Reply to a user to transfer cash.**",
            reply_markup=close_button(uid),
        )

    if len(m.command) < 2:
        return await m.reply_text(
            "💡 Usage: `/give 1000`",
            reply_markup=close_button(uid),
        )

    amount = parse_amount(m.command[1])

    if amount is None:
        return await m.reply_text(
            "❌ **Enter a valid positive amount.**",
            reply_markup=close_button(uid),
        )

    receiver = m.reply_to_message.from_user

    if receiver.id == uid:
        return await m.reply_text(
            "❌ **You cannot give yourself money.**",
            reply_markup=close_button(uid),
        )

    await ensure_user(receiver)

    balance = get_cash(uid)

    if balance < amount:
        return await m.reply_text(
            f"""
❌ **Insufficient Balance**

💰 Your cash: {money(balance)}
💸 Required: {money(amount)}
""",
            reply_markup=close_button(uid),
        )

    update_cash(uid, -amount)
    update_cash(receiver.id, amount)

    return await m.reply_text(
        f"""
╭━━━〔 💸 TRANSFER 〕━━━╮
│
│ 👤 From:
│ **{m.from_user.first_name}**
│
│ 🎯 To:
│ **{receiver.first_name}**
│
│ 💰 Amount:
│ **{money(amount)}**
│
│ ✅ Transfer successful!
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# ROB
# ============================================================

@bot.on_message(filters.command("rob"))
async def rob(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    robber = m.from_user
    uid = robber.id

    if not m.reply_to_message:
        return await m.reply_text(
            "💡 **Reply to a user to rob them.**",
            reply_markup=close_button(uid),
        )

    victim = m.reply_to_message.from_user
    await ensure_user(victim)

    if victim.id == uid:
        return await m.reply_text(
            "❌ **You cannot target yourself.**",
            reply_markup=close_button(uid),
        )

    remaining = cooldown_left("rob", uid)

    if remaining:
        return await m.reply_text(
            f"⏳ Rob cooldown: `{format_time(remaining)}`",
            reply_markup=close_button(uid),
        )

    set_cooldown("rob", uid)

    if get_protection(victim.id):
        return await m.reply_text(
            f"""
╭━━━〔 🛡️ PROTECTED 〕━━━╮
│
│ 🎯 Target:
│ **{victim.first_name}**
│
│ 🛡️ Their protection is active.
│
│ ❌ Robbery cancelled.
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
            reply_markup=close_button(uid),
        )

    victim_cash = get_cash(victim.id)

    if victim_cash <= 0:
        return await m.reply_text(
            "💸 **Target has no cash.**",
            reply_markup=close_button(uid),
        )

    if random.randint(1, 100) <= 60:
        amount = random.randint(
            max(1, int(victim_cash * 0.10)),
            max(1, int(victim_cash * 0.35)),
        )

        amount = min(amount, victim_cash)

        update_cash(victim.id, -amount)
        update_cash(uid, amount)

        return await m.reply_text(
            f"""
╭━━━〔 🥷 ROB SUCCESS 〕━━━╮
│
│ 🥷 Robber:
│ **{robber.first_name}**
│
│ 🎯 Target:
│ **{victim.first_name}**
│
│ 💰 Loot:
│ **+{money(amount)}**
│
│ ✅ Mission successful!
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
            reply_markup=close_button(uid),
        )

    penalty = min(
        random.randint(100, 800),
        get_cash(uid),
    )

    update_cash(uid, -penalty)

    return await m.reply_text(
        f"""
╭━━━〔 🚔 ROB FAILED 〕━━━╮
│
│ ❌ You were caught!
│
│ 💸 Fine:
│ **-{money(penalty)}**
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# ROB ALL
# ============================================================

@bot.on_message(filters.command("roball"))
async def roball(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    robber = m.from_user
    uid = robber.id

    if not m.reply_to_message:
        return await m.reply_text(
            "💡 **Reply to someone to use /roball.**",
            reply_markup=close_button(uid),
        )

    victim = m.reply_to_message.from_user
    await ensure_user(victim)

    if victim.id == uid:
        return await m.reply_text(
            "❌ **You cannot target yourself.**",
            reply_markup=close_button(uid),
        )

    if get_protection(victim.id):
        return await m.reply_text(
            "🛡️ **Target is protected. Robbery cancelled.**",
            reply_markup=close_button(uid),
        )

    victim_cash = get_cash(victim.id)

    if victim_cash <= 0:
        return await m.reply_text(
            "💸 **Target has no cash.**",
            reply_markup=close_button(uid),
        )

    if random.randint(1, 100) <= 55:
        percentage = random.randint(20, 60)
        amount = max(
            1,
            int(victim_cash * percentage / 100),
        )

        update_cash(victim.id, -amount)
        update_cash(uid, amount)

        return await m.reply_text(
            f"""
╭━━━〔 🏦 BIG ROBBERY 〕━━━╮
│
│ 🥷 **{robber.first_name}**
│
│ 🎯 Target:
│ **{victim.first_name}**
│
│ 📊 Looted:
│ `{percentage}%`
│
│ 💰 Amount:
│ **+{money(amount)}**
│
│ ✅ Successful!
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
            reply_markup=close_button(uid),
        )

    penalty = min(
        random.randint(100, 1000),
        get_cash(uid),
    )

    update_cash(uid, -penalty)

    return await m.reply_text(
        f"""
╭━━━〔 🚨 FAILED ROBBERY 〕━━━╮
│
│ ❌ Mission failed!
│
│ 💸 Fine:
│ **-{money(penalty)}**
│
╰━━━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# KILL
# ============================================================

@bot.on_message(filters.command("kill"))
async def kill(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    attacker = m.from_user
    uid = attacker.id

    if not m.reply_to_message:
        return await m.reply_text(
            "💡 **Reply to a player to use /kill.**",
            reply_markup=close_button(uid),
        )

    victim = m.reply_to_message.from_user
    await ensure_user(victim)

    if attacker.id == victim.id:
        return await m.reply_text(
            "❌ **You cannot target yourself.**",
            reply_markup=close_button(uid),
        )

    if victim.id in [
        getattr(bot, "owner_id", 0),
    ]:
        return await m.reply_text(
            "🛡️ **This player is protected from this action.**",
            reply_markup=close_button(uid),
        )

    protection = get_protection(victim.id)

    if protection:
        return await m.reply_text(
            f"""
🛡️ **PROTECTED PLAYER**

👤 Target: **{victim.first_name}**

Their protection is active.
""",
            reply_markup=close_button(uid),
        )

    victim_cash = get_cash(victim.id)

    loot = min(
        victim_cash,
        random.randint(100, 1500),
    )

    update_cash(victim.id, -loot)
    update_cash(uid, loot)

    try:
        update_kills(uid, 1)
    except Exception:
        pass

    return await m.reply_text(
        f"""
╭━━━〔 ⚔️ MISSION COMPLETE 〕━━━╮
│
│ ⚔️ Player:
│ **{attacker.first_name}**
│
│ 🎯 Target:
│ **{victim.first_name}**
│
│ 💰 Loot:
│ **+{money(loot)}**
│
│ 🏆 Total Kills:
│ `{get_kills(uid)}`
│
╰━━━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# KILLS
# ============================================================

@bot.on_message(filters.command("kills"))
async def kills(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id
    total = get_kills(uid)

    return await m.reply_text(
        f"""
╭━━━〔 ⚔️ KILL STATS 〕━━━╮
│
│ 👤 Player:
│ **{m.from_user.first_name}**
│
│ ⚔️ Total:
│ **{total}**
│
│ 🏆 Keep playing!
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# PROTECT
# ============================================================

@bot.on_message(filters.command("protect"))
async def protect(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    plans = {
        "1": (1000, 1),
        "2": (1800, 2),
        "3": (2500, 3),
    }

    if len(m.command) < 2:
        return await m.reply_text(
            """
╭━━━〔 🛡️ PROTECTION SHOP 〕━━━╮
│
│ `/protect 1`
│ 🛡️ 1 Day — ₹1,000
│
│ `/protect 2`
│ 🛡️ 2 Days — ₹1,800
│
│ `/protect 3`
│ 🛡️ 3 Days — ₹2,500
│
╰━━━━━━━━━━━━━━━━━━━━━━━━╯
""",
            reply_markup=close_button(uid),
        )

    if m.command[1] not in plans:
        return await m.reply_text(
            "❌ **Invalid protection plan.**",
            reply_markup=close_button(uid),
        )

    cost, days = plans[m.command[1]]
    balance = get_cash(uid)

    if balance < cost:
        return await m.reply_text(
            f"""
❌ **Not enough cash**

💰 Balance: {money(balance)}
💸 Required: {money(cost)}
""",
            reply_markup=close_button(uid),
        )

    update_cash(uid, -cost)

    expires = datetime.now() + timedelta(days=days)

    set_protection(uid, expires)

    return await m.reply_text(
        f"""
╭━━━〔 🛡️ SHIELD ACTIVE 〕━━━╮
│
│ 🛡️ Duration:
│ **{days} Day(s)**
│
│ 💰 Cost:
│ **{money(cost)}**
│
│ ⏰ Expires:
│ `{expires.strftime("%d-%m-%Y %H:%M")}`
│
│ 🔒 Protection activated!
│
╰━━━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# SHIELD
# ============================================================

@bot.on_message(filters.command("shield"))
async def shield(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id
    protection = get_protection(uid)

    if not protection:
        return await m.reply_text(
            """
╭━━━〔 🛡️ SHIELD 〕━━━╮
│
│ ❌ No active protection.
│
│ Use:
│ `/protect 1`
│ `/protect 2`
│ `/protect 3`
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
            reply_markup=close_button(uid),
        )

    return await m.reply_text(
        f"""
╭━━━〔 🛡️ SHIELD STATUS 〕━━━╮
│
│ 🔐 Status:
│ **ACTIVE**
│
│ ⏰ Protection:
│ `{protection}`
│
│ 🚫 Robbery protection enabled.
│
╰━━━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# BANK
# ============================================================

@bot.on_message(filters.command("bank"))
async def bank(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    cash = get_cash(uid)
    bank_money = get_bank(uid)

    return await m.reply_text(
        f"""
╭━━━〔 🏦 BANK 〕━━━╮
│
│ 👤 **{m.from_user.first_name}**
│
│ 💵 Cash:
│ **{money(cash)}**
│
│ 🏦 Bank:
│ **{money(bank_money)}**
│
│ 💎 Total:
│ **{money(cash + bank_money)}**
│
╰━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# DEPOSIT
# ============================================================

@bot.on_message(filters.command("deposit"))
async def deposit(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    if len(m.command) < 2:
        return await m.reply_text(
            "💡 Usage: `/deposit 1000`",
            reply_markup=close_button(uid),
        )

    amount = parse_amount(m.command[1])

    if amount is None:
        return await m.reply_text(
            "❌ **Invalid amount.**",
            reply_markup=close_button(uid),
        )

    cash = get_cash(uid)

    if cash < amount:
        return await m.reply_text(
            f"""
❌ **Insufficient Cash**

💵 Cash: {money(cash)}
💸 Deposit: {money(amount)}
""",
            reply_markup=close_button(uid),
        )

    update_cash(uid, -amount)
    add_bank(uid, amount)

    return await m.reply_text(
        f"""
╭━━━〔 🏦 DEPOSIT 〕━━━╮
│
│ 💰 Deposited:
│ **{money(amount)}**
│
│ 🏦 Bank:
│ **{money(get_bank(uid))}**
│
│ ✅ Successful!
│
╰━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# WITHDRAW
# ============================================================

@bot.on_message(filters.command("withdraw"))
async def withdraw(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    if len(m.command) < 2:
        return await m.reply_text(
            "💡 Usage: `/withdraw 1000`",
            reply_markup=close_button(uid),
        )

    amount = parse_amount(m.command[1])

    if amount is None:
        return await m.reply_text(
            "❌ **Invalid amount.**",
            reply_markup=close_button(uid),
        )

    bank_money = get_bank(uid)

    if bank_money < amount:
        return await m.reply_text(
            f"""
❌ **Insufficient Bank Balance**

🏦 Bank: {money(bank_money)}
💸 Withdraw: {money(amount)}
""",
            reply_markup=close_button(uid),
        )

    remove_bank(uid, amount)
    update_cash(uid, amount)

    return await m.reply_text(
        f"""
╭━━━〔 💵 WITHDRAW 〕━━━╮
│
│ 💰 Withdrawn:
│ **{money(amount)}**
│
│ 💵 Cash:
│ **{money(get_cash(uid))}**
│
│ 🏦 Bank:
│ **{money(get_bank(uid))}**
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# RICH LIST
# ============================================================

@bot.on_message(
    filters.command(
        ["richlist", "leaderboard", "top"]
    )
)
async def richlist(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    rich = get_richlist()

    text = """
╭━━━〔 👑 RICH LIST 〕━━━╮
│
"""

    if not rich:
        text += "│ ❌ No players found.\n"

    else:
        medals = {
            1: "🥇",
            2: "🥈",
            3: "🥉",
        }

        for index, user in enumerate(
            rich[:10],
            1,
        ):
            try:
                name = user.get(
                    "name",
                    "Unknown",
                )

                cash = user.get(
                    "cash",
                    0,
                )

            except Exception:
                name = "Unknown"
                cash = 0

            medal = medals.get(
                index,
                f"#{index}",
            )

            text += (
                f"│ {medal} **{name}**\n"
                f"│    💰 {money(cash)}\n"
            )

    text += """
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
"""

    return await m.reply_text(
        text,
        reply_markup=close_button(uid),
    )


# ============================================================
# BEG
# ============================================================

@bot.on_message(filters.command("beg"))
async def beg(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    remaining = cooldown_left("beg", uid)

    if remaining:
        return await m.reply_text(
            f"""
🥺 **Nobody is giving you money.**

⏳ Try again in:
`{format_time(remaining)}`
""",
            reply_markup=close_button(uid),
        )

    reward = random.randint(50, 500)

    if random.randint(1, 100) <= 10:
        reward *= 5
        event = "💎 Someone was extremely generous!"

    else:
        event = "🙏 Someone gave you some cash."

    update_cash(uid, reward)
    set_cooldown("beg", uid)

    return await m.reply_text(
        f"""
╭━━━〔 🥺 BEG 〕━━━╮
│
│ {event}
│
│ 💰 Received:
│ **+{money(reward)}**
│
╰━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# FLIP
# ============================================================

@bot.on_message(filters.command("flip"))
async def flip(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    if len(m.command) < 2:
        return await m.reply_text(
            "💡 Usage: `/flip 1000`",
            reply_markup=close_button(uid),
        )

    amount = parse_amount(m.command[1])

    if amount is None:
        return await m.reply_text(
            "❌ **Invalid amount.**",
            reply_markup=close_button(uid),
        )

    remaining = cooldown_left("flip", uid)

    if remaining:
        return await m.reply_text(
            f"⏳ Wait `{format_time(remaining)}`.",
            reply_markup=close_button(uid),
        )

    balance = get_cash(uid)

    if balance < amount:
        return await m.reply_text(
            f"""
❌ **Insufficient Balance**

💰 Balance: {money(balance)}
🎲 Bet: {money(amount)}
""",
            reply_markup=close_button(uid),
        )

    set_cooldown("flip", uid)

    if random.choice([True, False]):
        update_cash(uid, amount)

        result = f"""
🟢 **YOU WON!**

💰 Profit:
**+{money(amount)}**
"""

    else:
        update_cash(uid, -amount)

        result = f"""
🔴 **YOU LOST!**

💸 Lost:
**-{money(amount)}**
"""

    return await m.reply_text(
        f"""
╭━━━〔 🪙 COIN FLIP 〕━━━╮
│
│ 🎲 Bet:
│ **{money(amount)}**
│
{result}
│
│ 💵 Balance:
│ **{money(get_cash(uid))}**
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# PROFILE
# ============================================================

@bot.on_message(filters.command(["profile", "me"]))
async def profile(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    cash = get_cash(uid)
    bank_money = get_bank(uid)
    kills_count = get_kills(uid)

    try:
        data = get_profile(uid)
    except Exception:
        data = None

    name = m.from_user.first_name or "Unknown"

    if isinstance(data, dict):
        name = data.get(
            "name",
            name,
        )

    total = cash + bank_money

    return await m.reply_text(
        f"""
╭━━━〔 👤 PROFILE 〕━━━╮
│
│ 🪪 Name:
│ **{name}**
│
│ 💵 Cash:
│ **{money(cash)}**
│
│ 🏦 Bank:
│ **{money(bank_money)}**
│
│ 💎 Net Worth:
│ **{money(total)}**
│
│ ⚔️ Kills:
│ **{kills_count}**
│
│ 🎮 Status:
│ **ACTIVE**
│
╰━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# BONUS
# ============================================================

@bot.on_message(filters.command("bonus"))
async def bonus(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    remaining = cooldown_left("bonus", uid)

    if remaining:
        return await m.reply_text(
            f"""
🎁 **Bonus already claimed!**

⏳ Next bonus:
`{format_time(remaining)}`
""",
            reply_markup=close_button(uid),
        )

    reward = random.randint(2000, 8000)
    title = "🎁 BONUS CLAIMED"

    if random.randint(1, 100) == 1:
        reward += 50000
        title = "💎 MEGA BONUS"

    update_cash(uid, reward)
    set_cooldown("bonus", uid)

    return await m.reply_text(
        f"""
╭━━━〔 {title} 〕━━━╮
│
│ 👤 {m.from_user.first_name}
│
│ 💰 Reward:
│ **+{money(reward)}**
│
╰━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# MINE
# ============================================================

@bot.on_message(filters.command("mine"))
async def mine(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    remaining = cooldown_left("mine", uid)

    if remaining:
        return await m.reply_text(
            f"""
⛏️ **Mine is recharging**

⏳ `{format_time(remaining)}`
""",
            reply_markup=close_button(uid),
        )

    set_cooldown("mine", uid)

    outcomes = [
        ("🪨 Rocks", 100, 500),
        ("🪙 Coins", 300, 1200),
        ("💎 Rare Gem", 1500, 4000),
        ("💰 Treasure", 3000, 8000),
    ]

    item, low, high = random.choice(outcomes)

    reward = random.randint(
        low,
        high,
    )

    update_cash(uid, reward)

    return await m.reply_text(
        f"""
╭━━━〔 ⛏️ MINING 〕━━━╮
│
│ 🔎 Found:
│ **{item}**
│
│ 💰 Value:
│ **+{money(reward)}**
│
│ ⛏️ Mining successful!
│
╰━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# FISH
# ============================================================

@bot.on_message(filters.command("fish"))
async def fish(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    remaining = cooldown_left("fish", uid)

    if remaining:
        return await m.reply_text(
            f"""
🎣 **Fishing rod is resting**

⏳ `{format_time(remaining)}`
""",
            reply_markup=close_button(uid),
        )

    set_cooldown("fish", uid)

    catches = [
        ("🐟 Small Fish", 100, 400),
        ("🐠 Golden Fish", 500, 1500),
        ("🦈 Rare Catch", 1500, 5000),
        ("💎 Treasure Chest", 3000, 10000),
    ]

    item, low, high = random.choice(catches)

    reward = random.randint(
        low,
        high,
    )

    update_cash(uid, reward)

    return await m.reply_text(
        f"""
╭━━━〔 🎣 FISHING 〕━━━╮
│
│ 🌊 Catch:
│ **{item}**
│
│ 💰 Value:
│ **+{money(reward)}**
│
│ 🎣 Great catch!
│
╰━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# HUNT
# ============================================================

@bot.on_message(filters.command("hunt"))
async def hunt(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    remaining = cooldown_left("hunt", uid)

    if remaining:
        return await m.reply_text(
            f"""
🏹 **Hunt is on cooldown**

⏳ `{format_time(remaining)}`
""",
            reply_markup=close_button(uid),
        )

    set_cooldown("hunt", uid)

    rewards = [
        ("🐇 Rabbit", 200, 600),
        ("🦌 Deer", 500, 1800),
        ("🐗 Rare Find", 1000, 3000),
        ("💎 Ancient Treasure", 3000, 9000),
    ]

    item, low, high = random.choice(rewards)

    reward = random.randint(
        low,
        high,
    )

    update_cash(uid, reward)

    return await m.reply_text(
        f"""
╭━━━〔 🏹 HUNTING 〕━━━╮
│
│ 🔎 Found:
│ **{item}**
│
│ 💰 Reward:
│ **+{money(reward)}**
│
│ 🏹 Hunt complete!
│
╰━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# INVENTORY
# ============================================================

@bot.on_message(filters.command(["inventory", "inv"]))
async def inventory(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)

    uid = m.from_user.id

    try:
        items = get_inventory(uid)
    except Exception:
        items = {}

    icons = {
        "fish": "🐟",
        "gem": "💎",
        "gold": "🪙",
        "diamond": "💠",
        "treasure": "💰",
        "shield": "🛡️",
        "key": "🔑",
    }

    text = f"""
╭━━━〔 🎒 INVENTORY 〕━━━╮
│
│ 👤 **{m.from_user.first_name}**
│
"""

    if not items:
        text += "│ 📦 Inventory is empty.\n"

    elif isinstance(items, dict):

        for item, amount in items.items():

            icon = icons.get(
                str(item).lower(),
                "📦",
            )

            text += (
                f"│ {icon} **{item}** "
                f"× `{amount}`\n"
            )

    else:

        for item in items:
            text += f"│ 📦 **{item}**\n"

    text += """
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
"""

    return await m.reply_text(
        text,
        reply_markup=close_button(uid),
    )


# ============================================================
# XO — TIC TAC TOE
# ============================================================

def check_winner(board):
    wins = [
        [0, 1, 2],
        [3, 4, 5],
        [6, 7, 8],
        [0, 3, 6],
        [1, 4, 7],
        [2, 5, 8],
        [0, 4, 8],
        [2, 4, 6],
    ]

    for a, b, c in wins:

        if (
            board[a]
            == board[b]
            == board[c]
            and board[a] != " "
        ):
            return board[a]

    if " " not in board:
        return "Draw"

    return None


def make_xo_board(game_id):
    game = xo_games.get(game_id)

    if not game:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ Game Closed",
                        callback_data="xo_closed",
                    )
                ]
            ]
        )

    board = game["board"]

    rows = []

    for start in range(0, 9, 3):

        row = []

        for index in range(
            start,
            start + 3,
        ):

            value = board[index]

            if value == " ":
                value = "⬜"

            row.append(
                InlineKeyboardButton(
                    value,
                    callback_data=(
                        f"xo:{game_id}:{index}"
                    ),
                )
            )

        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                "🏳️ Forfeit",
                callback_data=(
                    f"xo_forfeit:{game_id}"
                ),
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


def xo_text(game):
    mode = game.get(
        "mode",
        "bot",
    )

    if mode == "pvp":

        p1 = game["player1_name"]
        p2 = game["player2_name"]

        turn_name = (
            p1
            if game["turn"] == "X"
            else p2
        )

        return f"""
╭━━━〔 🎮 TIC-TAC-TOE 〕━━━╮
│
│ ❌ **{p1}**
│ ⭕ **{p2}**
│
│ 🎯 Turn:
│ **{turn_name}**
│
│ 🔹 ❌ = {p1}
│ 🔸 ⭕ = {p2}
│
│ 🏆 PvP MODE
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
"""

    return f"""
╭━━━〔 🤖 TIC-TAC-TOE 〕━━━╮
│
│ 👤 **{game["player_name"]}**
│ 🤖 **AR Bot**
│
│ 🎯 Your symbol:
│ **❌**
│
│ 🤖 Bot:
│ **⭕**
│
│ 🎮 Your turn!
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
"""


def xo_winner_text(game, winner):
    if winner == "Draw":
        return """
╭━━━〔 🤝 GAME DRAW 〕━━━╮
│
│ 🤝 Nobody won!
│
│ 🎮 Great game.
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
"""

    if winner == "X":
        name = game.get(
            "player1_name",
            "Player",
        )
    else:
        if game.get("mode") == "pvp":
            name = game.get(
                "player2_name",
                "Player",
            )
        else:
            name = "AR Bot 🤖"

    return f"""
╭━━━〔 🏆 WINNER 〕━━━╮
│
│ 👑 Winner:
│ **{name}**
│
│ 🎯 Symbol:
│ **{winner}**
│
│ 🎉 Congratulations!
│
╰━━━━━━━━━━━━━━━━━━━━╯
"""


def bot_move(board):
    empty = [
        index
        for index, value in enumerate(board)
        if value == " "
    ]

    if not empty:
        return None

    # Try winning
    for index in empty:

        test = board.copy()
        test[index] = "O"

        if check_winner(test) == "O":
            return index

    # Block player
    for index in empty:

        test = board.copy()
        test[index] = "X"

        if check_winner(test) == "X":
            return index

    # Center
    if 4 in empty:
        return 4

    # Corners
    corners = [
        x for x in [0, 2, 6, 8]
        if x in empty
    ]

    if corners:
        return random.choice(corners)

    return random.choice(empty)


@bot.on_message(filters.command("xo"))
async def xo_start(_, m):
    await delete_command(m)

    await ensure_user(m.from_user)

    player = m.from_user

    # ========================================================
    # PVP
    # ========================================================

    if m.reply_to_message:

        opponent = m.reply_to_message.from_user

        if opponent.id == player.id:
            return await m.reply_text(
                "❌ **You cannot play against yourself.**",
                reply_markup=close_button(
                    player.id
                ),
            )

        if opponent.is_bot:
            return await m.reply_text(
                "❌ **Bots cannot play PvP XO.**",
                reply_markup=close_button(
                    player.id
                ),
            )

        await ensure_user(opponent)

        game_id = (
            f"{player.id}_"
            f"{opponent.id}_"
            f"{random.randint(1000, 9999)}"
        )

        xo_games[game_id] = {
            "mode": "pvp",
            "player1": player.id,
            "player2": opponent.id,
            "player1_name": (
                player.first_name
                or "Player 1"
            ),
            "player2_name": (
                opponent.first_name
                or "Player 2"
            ),
            "board": [
                " ",
                " ",
                " ",
                " ",
                " ",
                " ",
                " ",
                " ",
                " ",
            ],
            "turn": "X",
            "message_id": None,
        }

        game = xo_games[game_id]

        sent = await m.reply_text(
            xo_text(game),
            reply_markup=make_xo_board(
                game_id
            ),
        )

        game["message_id"] = sent.id

        return

    # ========================================================
    # BOT MODE
    # ========================================================

    game_id = (
        f"bot_{player.id}_"
        f"{random.randint(1000, 9999)}"
    )

    xo_games[game_id] = {
        "mode": "bot",
        "player": player.id,
        "player_name": (
            player.first_name
            or "Player"
        ),
        "board": [
            " ",
            " ",
            " ",
            " ",
            " ",
            " ",
            " ",
            " ",
            " ",
        ],
        "turn": "X",
        "message_id": None,
    }

    game = xo_games[game_id]

    sent = await m.reply_text(
        xo_text(game),
        reply_markup=make_xo_board(
            game_id
        ),
    )

    game["message_id"] = sent.id


# ============================================================
# XO CALLBACK
# ============================================================

@bot.on_callback_query(
    filters.regex(r"^xo:")
)
async def xo_callback(_, query):
    data = query.data.split(":")

    if len(data) != 3:
        return await query.answer(
            "Invalid move.",
            show_alert=True,
        )

    game_id = data[1]

    try:
        position = int(data[2])
    except Exception:
        return await query.answer(
            "Invalid position.",
            show_alert=True,
        )

    game = xo_games.get(game_id)

    if not game:
        return await query.answer(
            "❌ Game has ended.",
            show_alert=True,
        )

    if position < 0 or position > 8:
        return await query.answer(
            "Invalid move.",
            show_alert=True,
        )

    uid = query.from_user.id

    # ========================================================
    # PVP MODE
    # ========================================================

    if game["mode"] == "pvp":

        if uid not in [
            game["player1"],
            game["player2"],
        ]:
            return await query.answer(
                "❌ You are not part of this game.",
                show_alert=True,
            )

        current_symbol = game["turn"]

        current_player = (
            game["player1"]
            if current_symbol == "X"
            else game["player2"]
        )

        if uid != current_player:
            return await query.answer(
                "⏳ It's not your turn!",
                show_alert=True,
            )

        if game["board"][position] != " ":
            return await query.answer(
                "❌ This box is already occupied.",
                show_alert=True,
            )

        game["board"][position] = current_symbol

        result = check_winner(
            game["board"]
        )

        if result:

            text = xo_winner_text(
                game,
                result,
            )

            # IMPORTANT:
            # No cash reward in PvP.
            del xo_games[game_id]

            return await query.message.edit_text(
                text
            )

        game["turn"] = (
            "O"
            if current_symbol == "X"
            else "X"
        )

        await query.answer(
            "Move played!"
        )

        return await query.message.edit_text(
            xo_text(game),
            reply_markup=make_xo_board(
                game_id
            ),
        )

    # ========================================================
    # BOT MODE
    # ========================================================

    if uid != game["player"]:
        return await query.answer(
            "❌ This game belongs to another player.",
            show_alert=True,
        )

    if game["turn"] != "X":
        return await query.answer(
            "⏳ Bot is thinking...",
            show_alert=True,
        )

    if game["board"][position] != " ":
        return await query.answer(
            "❌ Box already occupied.",
            show_alert=True,
        )

    game["board"][position] = "X"

    result = check_winner(
        game["board"]
    )

    if result:

        text = xo_winner_text(
            game,
            result,
        )

        del xo_games[game_id]

        return await query.message.edit_text(
            text
        )

    game["turn"] = "O"

    bot_position = bot_move(
        game["board"]
    )

    if bot_position is not None:
        game["board"][bot_position] = "O"

    result = check_winner(
        game["board"]
    )

    if result:

        text = xo_winner_text(
            game,
            result,
        )

        del xo_games[game_id]

        return await query.message.edit_text(
            text
        )

    game["turn"] = "X"

    await query.answer(
        "🤖 Bot moved!"
    )

    return await query.message.edit_text(
        xo_text(game),
        reply_markup=make_xo_board(
            game_id
        ),
    )


# ============================================================
# XO FORFEIT
# ============================================================

@bot.on_callback_query(
    filters.regex(r"^xo_forfeit:")
)
async def xo_forfeit(_, query):
    game_id = query.data.split(
        ":",
        1,
    )[1]

    game = xo_games.get(game_id)

    if not game:
        return await query.answer(
            "Game already ended.",
            show_alert=True,
        )

    uid = query.from_user.id

    allowed = []

    if game["mode"] == "pvp":
        allowed = [
            game["player1"],
            game["player2"],
        ]

    else:
        allowed = [
            game["player"],
        ]

    if uid not in allowed:
        return await query.answer(
            "❌ This is not your game.",
            show_alert=True,
        )

    if game["mode"] == "pvp":

        if uid == game["player1"]:
            winner = game["player2"]
            winner_name = game[
                "player2_name"
            ]

        else:
            winner = game["player1"]
            winner_name = game[
                "player1_name"
            ]

        del xo_games[game_id]

        return await query.message.edit_text(
            f"""
╭━━━〔 🏳️ FORFEIT 〕━━━╮
│
│ 🏆 Winner:
│ **{winner_name}**
│
│ 🎮 Opponent forfeited.
│
│ 💰 PvP cash reward:
│ **None**
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
"""
        )

    del xo_games[game_id]

    return await query.message.edit_text(
        """
╭━━━〔 🏳️ GAME ENDED 〕━━━╮
│
│ ❌ You forfeited the game.
│
│ 🤖 Bot wins!
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
"""
    )


# ============================================================
# XO CLOSED
# ============================================================

@bot.on_callback_query(
    filters.regex("^xo_closed$")
)
async def xo_closed(_, query):
    return await query.answer(
        "❌ This game is already closed.",
        show_alert=True,
    )


# ============================================================
# XO ACTIVE GAMES
# ============================================================

@bot.on_message(filters.command("xogames"))
async def xo_games_list(_, m):
    await delete_command(m)

    uid = m.from_user.id

    count = len(xo_games)

    return await m.reply_text(
        f"""
╭━━━〔 🎮 XO SERVER 〕━━━╮
│
│ 🎯 Active Games:
│ **{count}**
│
│ 🎮 Mode:
│ **Tic-Tac-Toe**
│
│ 💡 Start:
│ `/xo`
│
│ 👥 PvP:
│ Reply to a player with `/xo`
│
╰━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# GAME HELP
# ============================================================

@bot.on_message(
    filters.command(
        ["gamehelp", "games"]
    )
)
async def gamehelp(_, m):
    await delete_command(m)

    uid = m.from_user.id

    return await m.reply_text(
        """
╭━━━〔 🎮 AR GAME CENTER 〕━━━╮
│
│ 💰 ECONOMY
│ ├ /bal
│ ├ /daily
│ ├ /work
│ ├ /beg
│ ├ /bonus
│ ├ /give
│ └ /profile
│
│ 🏦 BANK
│ ├ /bank
│ ├ /deposit
│ └ /withdraw
│
│ 🛡️ SECURITY
│ ├ /protect
│ └ /shield
│
│ ⚔️ ACTION
│ ├ /crime
│ ├ /rob
│ ├ /roball
│ ├ /kill
│ └ /kills
│
│ 🎮 GAMES
│ ├ /xo
│ ├ /xogames
│ └ /flip
│
│ 🌎 ADVENTURE
│ ├ /arworld
│ ├ /mine
│ ├ /fish
│ └ /hunt
│
│ 👑 SOCIAL
│ ├ /richlist
│ └ /inventory
│
╰━━━━━━━━━━━━━━━━━━━━━━━━╯
""",
        reply_markup=close_button(uid),
    )


# ============================================================
# CLOSE CALLBACK
# ============================================================

@bot.on_callback_query(
    filters.regex(r"^close_")
)
async def close_callback(_, query):

    try:
        user_id = int(
            query.data.split("_")[1]
        )

    except Exception:
        return await query.answer(
            "Invalid button.",
            show_alert=True,
        )

    if query.from_user.id != user_id:
        return await query.answer(
            "⚠️ Ye button aapka nahi hai!",
            show_alert=True,
        )

    try:
        await query.message.delete()

    except Exception:
        try:
            await query.answer(
                "Already closed."
            )
        except Exception:
            pass
