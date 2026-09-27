# ============================================================
#                    AR WORLD PRO GAME BOT
#                  COMPLETE ADVANCED GAME.PY (V3.0)
# ============================================================

import random
import asyncio
from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
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
# GLOBAL DATA & CONFIG
# ============================================================

xo_games = {}
arworld_cd = {}

game_cooldowns = {
    "daily": {}, "work": {}, "beg": {}, "bonus": {},
    "mine": {}, "fish": {}, "hunt": {}, "flip": {},
    "crime": {}, "rob": {},
}

COOLDOWN_TIME = {
    "daily": 86400, "work": 3600, "beg": 300,
    "bonus": 43200, "mine": 180, "fish": 180,
    "hunt": 300, "flip": 10, "crime": 120, "rob": 180,
}

# Pro UI Styling Constants
BOX_START = "╭━━━〔 🌟 AR WORLD PRO 〕━━━╮\n│\n"
BOX_END = "│\n╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
LINE_SEP = "├──────────────────────────────"

# ============================================================
# COMMON HELPERS
# ============================================================

def close_button(user_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Close Menu", callback_data=f"close_{user_id}")]
    ])

async def delete_command(message):
    try:
        await message.delete()
    except Exception:
        pass

async def ensure_user(user):
    try:
        await register_user(user.id)
        await update_name(user.id, user.first_name or "Unknown")
    except Exception:
        pass

def parse_amount(value):
    try:
        amount = int(str(value).replace(',', '').replace('.', ''))
        return amount if amount > 0 else None
    except Exception:
        return None

def now_ts():
    import time
    return time.time()

def cooldown_left(command, user_id):
    last = game_cooldowns.get(command, {}).get(user_id)
    if not last: return 0
    remaining = COOLDOWN_TIME[command] - (now_ts() - last)
    return max(0, int(remaining))

def set_cooldown(command, user_id):
    if command not in game_cooldowns:
        game_cooldowns[command] = {}
    game_cooldowns[command][user_id] = now_ts()

def format_time(seconds):
    seconds = int(seconds)
    if seconds <= 0: return "✅ Ready"
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    if h: return f"{h}h {m}m"
    if m: return f"{m}m {s}s"
    return f"{s}s"

def money(amount):
    return f"💸 ₹{int(amount):,}"

# ============================================================
# 🌎 AR WORLD (Adventure)
# ============================================================

ARWORLD_EVENTS = [
    ("💎 Hidden Treasure Found!", 1000, 5000),
    ("🪙 Ancient Coin Stash", 500, 2500),
    ("🏆 Secret Mission Complete", 1500, 6000),
    ("📦 Mysterious Package", 300, 2000),
    ("💼 High-Paying Gig", 700, 3500),
    ("🌟 Rare Artifact Discovery", 2000, 8000),
]

@bot.on_message(filters.command("arworld"))
async def arworld(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    current = now_ts()
    last = arworld_cd.get(uid, 0)
    
    if current - last < 30:
        rem = int(30 - (current - last))
        return await m.reply_text(f"{BOX_START}│ ⏳ **World Recharging...**\n│ Try again in: `{rem}s`\n{BOX_END}", reply_markup=close_button(uid))

    arworld_cd[uid] = current
    event_text, min_r, max_r = random.choice(ARWORLD_EVENTS)
    reward = random.randint(min_r, max_r)
    
    bonus_txt = ""
    if random.randint(1, 100) <= 10:
        bonus = random.randint(3000, 7000)
        reward += bonus
        bonus_txt = f"│ 🔥 **Lucky Bonus:** +{money(bonus)}\n"
    
    locations = ["🏙️ Neon City", "🌲 Dark Forest", "🏜️ Lost Desert", "🏝️ Mystery Island", "🏰 Ancient Castle", "🌌 Shadow Valley"]
    
    update_cash(uid, reward)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 📍 **Location:** {random.choice(locations)}\n"
        f"│\n"
        f"│ {event_text}\n"
        f"│ 💰 **Reward:** +{money(reward)}\n"
        f"{bonus_txt}"
        f"│\n"
        f"│ 🎒 Adventure Completed!\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

# ============================================================
# 💰 ECONOMY COMMANDS
# ============================================================

@bot.on_message(filters.command(["bal", "balance"]))
async def balance(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    cash = get_cash(uid)
    bank = get_bank(uid)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 👤 **Player:** {m.from_user.first_name}\n"
        f"{LINE_SEP}\n"
        f"│ 💵 **Cash:** {money(cash)}\n"
        f"│ 🏦 **Bank:** {money(bank)}\n"
        f"{LINE_SEP}\n"
        f"│ 💎 **Net Worth:** {money(cash + bank)}\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("daily"))
async def daily(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if cooldown_left("daily", uid):
        return await m.reply_text(f"{BOX_START}│ ❌ **Already Claimed!**\n│ ⏳ Next: `{format_time(cooldown_left('daily', uid))}`\n{BOX_END}", reply_markup=close_button(uid))
    
    reward = random.randint(1000, 5000)
    title = "🎁 Daily Reward"
    
    if random.randint(1, 100) <= 5:
        reward += random.randint(5000, 15000)
        title = "💎 DAILY JACKPOT!"
        
    update_cash(uid, reward)
    set_cooldown("daily", uid)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ {title}\n"
        f"│ 👤 {m.from_user.first_name}\n"
        f"│ 💰 Received: **+{money(reward)}**\n"
        f"│\n"
        f"│ 🔥 Come back tomorrow!\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("work"))
async def work(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if cooldown_left("work", uid):
        return await m.reply_text(f"{BOX_START}│ 😴 **You are tired!**\n│ Rest for: `{format_time(cooldown_left('work', uid))}`\n{BOX_END}", reply_markup=close_button(uid))
    
    jobs = [("💻 Coder", 500, 2500), ("🎨 Designer", 400, 2200), ("🚕 Driver", 500, 2500), ("🍕 Delivery", 300, 1800), ("🧑‍🍳 Chef", 350, 2000)]
    job, low, high = random.choice(jobs)
    reward = random.randint(low, high)
    
    update_cash(uid, reward)
    set_cooldown("work", uid)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 💼 **Work Complete**\n"
        f"│ Job: {job}\n"
        f"│ Earned: **+{money(reward)}**\n"
        f"│\n"
        f"│ ⚡ Hard work pays!\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("crime"))
async def crime(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if cooldown_left("crime", uid):
        return await m.reply_text(f"{BOX_START}│ 🚨 **Cooldown Active**\n│ Try again in: `{format_time(cooldown_left('crime', uid))}`\n{BOX_END}", reply_markup=close_button(uid))
    
    set_cooldown("crime", uid)
    
    if random.randint(1, 100) <= 65:
        reward = random.randint(500, 4000)
        update_cash(uid, reward)
        await m.reply_text(
            f"{BOX_START}"
            f"│ 🚨 **Crime Successful!**\n"
            f"│ You escaped with the loot.\n"
            f"│ 💰 Loot: **+{money(reward)}**\n"
            f"{BOX_END}", reply_markup=close_button(uid)
        )
    else:
        fine = min(random.randint(200, 1200), get_cash(uid))
        update_cash(uid, -fine)
        await m.reply_text(
            f"{BOX_START}"
            f"│ 🚔 **Busted!**\n"
            f"│ The police caught you.\n"
            f"│ 💸 Fine Paid: **-{money(fine)}**\n"
            f"{BOX_END}", reply_markup=close_button(uid)
        )

@bot.on_message(filters.command("give"))
async def give(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if not m.reply_to_message:
        return await m.reply_text("❌ **Reply to a user to transfer cash.**", reply_markup=close_button(uid))
    if len(m.command) < 2:
        return await m.reply_text("💡 Usage: `/give 1000`", reply_markup=close_button(uid))
        
    amount = parse_amount(m.command[1])
    if amount is None:
        return await m.reply_text("❌ **Enter a valid positive amount.**", reply_markup=close_button(uid))
        
    receiver = m.reply_to_message.from_user
    if receiver.id == uid:
        return await m.reply_text("❌ **You cannot give yourself money.**", reply_markup=close_button(uid))
        
    await ensure_user(receiver)
    balance = get_cash(uid)
    
    if balance < amount:
        return await m.reply_text(f"❌ **Insufficient Balance**\n💰 Your cash: {money(balance)}\n💸 Required: {money(amount)}", reply_markup=close_button(uid))
    
    update_cash(uid, -amount)
    update_cash(receiver.id, amount)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 💸 **TRANSFER SUCCESSFUL**\n"
        f"│\n"
        f"│ 👤 From: **{m.from_user.first_name}**\n"
        f"│ 🎯 To: **{receiver.first_name}**\n"
        f"│ 💰 Amount: **{money(amount)}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

# ============================================================
# ⚔️ KILL & ROB SYSTEM (ADVANCED WITH ANIMATION)
# ============================================================

@bot.on_message(filters.command("kill"))
async def kill(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    
    attacker = m.from_user
    uid = attacker.id
    
    if not m.reply_to_message:
        return await m.reply_text("💡 **Reply to a user to /kill them.**", reply_markup=close_button(uid))
    
    victim = m.reply_to_message.from_user
    await ensure_user(victim)
    
    if victim.id == uid:
        return await m.reply_text("❌ **Suicide is not allowed!**", reply_markup=close_button(uid))
    if victim.id == getattr(bot, "owner_id", 0):
        return await m.reply_text("🛡️ **This player is protected by the system.**", reply_markup=close_button(uid))
    
    if get_protection(victim.id):
        return await m.reply_text(
            f"{BOX_START}"
            f"│ 🛡️ **Protected Target**\n"
            f"│ {victim.first_name} has an active shield.\n"
            f"│ ❌ Attack Blocked!\n"
            f"{BOX_END}", reply_markup=close_button(uid)
        )

    anim_msg = await m.reply_text(f"⚔️ **{attacker.first_name}** is preparing to attack **{victim.first_name}**...")
    await asyncio.sleep(1.5) # Advanced animation delay
    
    victim_cash = get_cash(victim.id)
    loot = min(victim_cash, random.randint(100, 1500))
    
    update_cash(victim.id, -loot)
    update_cash(uid, loot)
    update_kills(uid, 1)
    
    await anim_msg.edit_text(
        f"{BOX_START}"
        f"│ ⚔️ **MISSION ACCOMPLISHED**\n"
        f"│\n"
        f"│ 🔫 Attacker: **{attacker.first_name}**\n"
        f"│ 💀 Victim: **{victim.first_name}**\n"
        f"│\n"
        f"│ 💰 Loot Stolen: **+{money(loot)}**\n"
        f"│ 🏆 Total Kills: `{get_kills(uid)}`\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("rob"))
async def rob(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    
    robber = m.from_user
    uid = robber.id
    
    if not m.reply_to_message:
        return await m.reply_text("💡 **Reply to a user to /rob them.**", reply_markup=close_button(uid))
    
    victim = m.reply_to_message.from_user
    await ensure_user(victim)
    
    if victim.id == uid:
        return await m.reply_text("❌ **You cannot rob yourself.**", reply_markup=close_button(uid))
    if cooldown_left("rob", uid):
        return await m.reply_text(f"{BOX_START}│ ⏳ **Rob Cooldown:** `{format_time(cooldown_left('rob', uid))}`\n{BOX_END}", reply_markup=close_button(uid))
    
    set_cooldown("rob", uid)
    
    if get_protection(victim.id):
        return await m.reply_text(f"🛡️ **{victim.first_name}** is protected by a Shield!", reply_markup=close_button(uid))
    
    victim_cash = get_cash(victim.id)
    if victim_cash <= 0:
        return await m.reply_text("💸 **Target is broke!** Nothing to rob.", reply_markup=close_button(uid))
    
    anim_msg = await m.reply_text(f"🥷 **{robber.first_name}** is sneaking towards **{victim.first_name}**...")
    await asyncio.sleep(1.5)
    
    if random.randint(1, 100) <= 60:
        amount = random.randint(max(1, int(victim_cash * 0.10)), max(1, int(victim_cash * 0.35)))
        amount = min(amount, victim_cash)
        
        update_cash(victim.id, -amount)
        update_cash(uid, amount)
        
        await anim_msg.edit_text(
            f"{BOX_START}"
            f"│ 🥷 **ROBBERY SUCCESSFUL**\n"
            f"│\n"
            f"│ 🎯 Target: **{victim.first_name}**\n"
            f"│ 💰 Stolen: **+{money(amount)}**\n"
            f"│\n"
            f"│ ✅ You escaped safely!\n"
            f"{BOX_END}",
            reply_markup=close_button(uid)
        )
    else:
        penalty = min(random.randint(100, 800), get_cash(uid))
        update_cash(uid, -penalty)
        
        await anim_msg.edit_text(
            f"{BOX_START}"
            f"│ 🚔 **ROBBERY FAILED**\n"
            f"│\n"
            f"│ ❌ You were caught!\n"
            f"│ 💸 Fine Paid: **-{money(penalty)}**\n"
            f"{BOX_END}",
            reply_markup=close_button(uid)
        )

@bot.on_message(filters.command("roball"))
async def roball(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    
    robber = m.from_user
    uid = robber.id
    
    if not m.reply_to_message:
        return await m.reply_text("💡 **Reply to someone to use /roball.**", reply_markup=close_button(uid))
    
    victim = m.reply_to_message.from_user
    await ensure_user(victim)
    
    if victim.id == uid:
        return await m.reply_text("❌ **You cannot target yourself.**", reply_markup=close_button(uid))
    if get_protection(victim.id):
        return await m.reply_text("🛡️ **Target is protected. Robbery cancelled.**", reply_markup=close_button(uid))
    
    victim_cash = get_cash(victim.id)
    if victim_cash <= 0:
        return await m.reply_text("💸 **Target has no cash.**", reply_markup=close_button(uid))
    
    anim_msg = await m.reply_text(f"🏦 **{robber.first_name}** is attempting a HEIST on **{victim.first_name}**...")
    await asyncio.sleep(2)
    
    if random.randint(1, 100) <= 55:
        percentage = random.randint(20, 60)
        amount = max(1, int(victim_cash * percentage / 100))
        
        update_cash(victim.id, -amount)
        update_cash(uid, amount)
        
        await anim_msg.edit_text(
            f"{BOX_START}"
            f"│ 🏦 **BIG ROBBERY SUCCESS**\n"
            f"│\n"
            f"│ 🥷 Robber: **{robber.first_name}**\n"
            f"│ 🎯 Target: **{victim.first_name}**\n"
            f"│ 📊 Looted: `{percentage}%`\n"
            f"│ 💰 Amount: **+{money(amount)}**\n"
            f"{BOX_END}",
            reply_markup=close_button(uid)
        )
    else:
        penalty = min(random.randint(500, 2000), get_cash(uid))
        update_cash(uid, -penalty)
        
        await anim_msg.edit_text(
            f"{BOX_START}"
            f"│ 🚨 **HEIST FAILED**\n"
            f"│\n"
            f"│ ❌ Mission failed! Heavy security.\n"
            f"│ 💸 Fine Paid: **-{money(penalty)}**\n"
            f"{BOX_END}",
            reply_markup=close_button(uid)
        )

@bot.on_message(filters.command("protect"))
async def protect(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    plans = {"1": (1000, 1), "2": (1800, 2), "3": (2500, 3)}
    
    if len(m.command) < 2 or m.command[1] not in plans:
        return await m.reply_text(
            f"{BOX_START}"
            f"│ 🛡️ **SHIELD SHOP**\n"
            f"│\n"
            f"│ 1️⃣ Day 1: ₹1,000 (`/protect 1`)\n"
            f"│ 2️⃣ Days 2: ₹1,800 (`/protect 2`)\n"
            f"│ 3️⃣ Days 3: ₹2,500 (`/protect 3`)\n"
            f"{BOX_END}",
            reply_markup=close_button(uid)
        )
        
    cost, days = plans[m.command[1]]
    if get_cash(uid) < cost:
        return await m.reply_text(f"❌ **Insufficient Funds.** Need {money(cost)}", reply_markup=close_button(uid))
    
    update_cash(uid, -cost)
    expires = datetime.now() + timedelta(days=days)
    set_protection(uid, expires)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 🛡️ **SHIELD ACTIVATED**\n"
        f"│\n"
        f"│ ⏳ Duration: **{days} Days**\n"
        f"│ 💰 Cost: **{money(cost)}**\n"
        f"│ 🔒 Expires: `{expires.strftime('%d-%m-%Y %H:%M')}`\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("shield"))
async def shield(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    protection = get_protection(uid)
    
    if not protection:
        return await m.reply_text(
            f"{BOX_START}"
            f"│ 🛡️ **SHIELD STATUS**\n"
            f"│\n"
            f"│ ❌ No active protection.\n"
            f"│ Use: `/protect 1`, `/protect 2`, `/protect 3`\n"
            f"{BOX_END}",
            reply_markup=close_button(uid)
        )
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 🛡️ **SHIELD STATUS**\n"
        f"│\n"
        f"│ 🔐 Status: **ACTIVE**\n"
        f"│ ⏰ Protection: `{protection}`\n"
        f"│ 🚫 Robbery & Kill protection enabled.\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("kills"))
async def kills(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    total = get_kills(uid)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ ⚔️ **KILL STATS**\n"
        f"│\n"
        f"│ 👤 Player: **{m.from_user.first_name}**\n"
        f"│ ⚔️ Total Kills: **{total}**\n"
        f"│\n"
        f"│ 🏆 Keep playing!\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

# ============================================================
# 🏦 BANKING SYSTEM
# ============================================================

@bot.on_message(filters.command("bank"))
async def bank(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    cash = get_cash(uid)
    bank_money = get_bank(uid)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 🏦 **BANK STATEMENT**\n"
        f"│\n"
        f"│ 👤 **{m.from_user.first_name}**\n"
        f"{LINE_SEP}\n"
        f"│ 💵 Cash: **{money(cash)}**\n"
        f"│ 🏦 Bank: **{money(bank_money)}**\n"
        f"{LINE_SEP}\n"
        f"│ 💎 Total: **{money(cash + bank_money)}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("deposit"))
async def deposit(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if len(m.command) < 2:
        return await m.reply_text("💡 Usage: `/deposit 1000`", reply_markup=close_button(uid))
    amount = parse_amount(m.command[1])
    if amount is None:
        return await m.reply_text("❌ **Invalid amount.**", reply_markup=close_button(uid))
        
    cash = get_cash(uid)
    if cash < amount:
        return await m.reply_text(f"❌ **Insufficient Cash**\n💵 Cash: {money(cash)}\n💸 Deposit: {money(amount)}", reply_markup=close_button(uid))
    
    update_cash(uid, -amount)
    add_bank(uid, amount)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 🏦 **DEPOSIT SUCCESSFUL**\n"
        f"│\n"
        f"│ 💰 Deposited: **{money(amount)}**\n"
        f"│ 🏦 New Bank Balance: **{money(get_bank(uid))}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("withdraw"))
async def withdraw(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if len(m.command) < 2:
        return await m.reply_text("💡 Usage: `/withdraw 1000`", reply_markup=close_button(uid))
    amount = parse_amount(m.command[1])
    if amount is None:
        return await m.reply_text("❌ **Invalid amount.**", reply_markup=close_button(uid))
        
    bank_money = get_bank(uid)
    if bank_money < amount:
        return await m.reply_text(f"❌ **Insufficient Bank Balance**\n🏦 Bank: {money(bank_money)}\n💸 Withdraw: {money(amount)}", reply_markup=close_button(uid))
    
    remove_bank(uid, amount)
    update_cash(uid, amount)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 💵 **WITHDRAW SUCCESSFUL**\n"
        f"│\n"
        f"│ 💰 Withdrawn: **{money(amount)}**\n"
        f"│ 💵 New Cash: **{money(get_cash(uid))}**\n"
        f"│ 🏦 New Bank: **{money(get_bank(uid))}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

# ============================================================
# 🎲 GAMES & ADVENTURE
# ============================================================

@bot.on_message(filters.command("beg"))
async def beg(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if cooldown_left("beg", uid):
        return await m.reply_text(f"🥺 **Nobody is giving you money.**\n⏳ Try again in: `{format_time(cooldown_left('beg', uid))}`", reply_markup=close_button(uid))
    
    reward = random.randint(50, 500)
    event = "💎 Someone was extremely generous!" if random.randint(1, 100) <= 10 else "🙏 Someone gave you some cash."
    
    if "generous" in event: reward *= 5
        
    update_cash(uid, reward)
    set_cooldown("beg", uid)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 🥺 **BEGGING**\n"
        f"│\n"
        f"│ {event}\n"
        f"│ 💰 Received: **+{money(reward)}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("flip"))
async def flip(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if len(m.command) < 2:
        return await m.reply_text("💡 Usage: `/flip 1000`", reply_markup=close_button(uid))
    amount = parse_amount(m.command[1])
    if amount is None:
        return await m.reply_text("❌ **Invalid amount.**", reply_markup=close_button(uid))
    if cooldown_left("flip", uid):
        return await m.reply_text(f"⏳ Wait `{format_time(cooldown_left('flip', uid))}`.", reply_markup=close_button(uid))
        
    balance = get_cash(uid)
    if balance < amount:
        return await m.reply_text(f"❌ **Insufficient Balance**\n💰 Balance: {money(balance)}\n🎲 Bet: {money(amount)}", reply_markup=close_button(uid))
    
    set_cooldown("flip", uid)
    anim_msg = await m.reply_text("🪙 **Flipping the coin...**")
    await asyncio.sleep(1)
    
    if random.choice([True, False]):
        update_cash(uid, amount)
        await anim_msg.edit_text(
            f"{BOX_START}"
            f"│ 🪙 **COIN FLIP**\n"
            f"│\n"
            f"│ 🎲 Bet: **{money(amount)}**\n"
            f"│ 🟢 **YOU WON!**\n"
            f"│ 💰 Profit: **+{money(amount)}**\n"
            f"│ 💵 Balance: **{money(get_cash(uid))}**\n"
            f"{BOX_END}",
            reply_markup=close_button(uid)
        )
    else:
        update_cash(uid, -amount)
        await anim_msg.edit_text(
            f"{BOX_START}"
            f"│ 🪙 **COIN FLIP**\n"
            f"│\n"
            f"│ 🎲 Bet: **{money(amount)}**\n"
            f"│ 🔴 **YOU LOST!**\n"
            f"│ 💸 Lost: **-{money(amount)}**\n"
            f"│ 💵 Balance: **{money(get_cash(uid))}**\n"
            f"{BOX_END}",
            reply_markup=close_button(uid)
        )

@bot.on_message(filters.command("bonus"))
async def bonus(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if cooldown_left("bonus", uid):
        return await m.reply_text(f"🎁 **Bonus already claimed!**\n⏳ Next bonus: `{format_time(cooldown_left('bonus', uid))}`", reply_markup=close_button(uid))
    
    reward = random.randint(2000, 8000)
    title = "🎁 BONUS CLAIMED"
    
    if random.randint(1, 100) == 1:
        reward += 50000
        title = "💎 MEGA BONUS"
        
    update_cash(uid, reward)
    set_cooldown("bonus", uid)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ {title}\n"
        f"│ 👤 {m.from_user.first_name}\n"
        f"│ 💰 Reward: **+{money(reward)}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("mine"))
async def mine(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if cooldown_left("mine", uid):
        return await m.reply_text(f"⛏️ **Mine is recharging**\n⏳ `{format_time(cooldown_left('mine', uid))}`", reply_markup=close_button(uid))
    
    set_cooldown("mine", uid)
    outcomes = [("🪨 Rocks", 100, 500), ("🪙 Coins", 300, 1200), ("💎 Rare Gem", 1500, 4000), ("💰 Treasure", 3000, 8000)]
    item, low, high = random.choice(outcomes)
    reward = random.randint(low, high)
    update_cash(uid, reward)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ ⛏️ **MINING SUCCESS**\n"
        f"│\n"
        f"│ 🔎 Found: **{item}**\n"
        f"│ 💰 Value: **+{money(reward)}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("fish"))
async def fish(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if cooldown_left("fish", uid):
        return await m.reply_text(f"🎣 **Fishing rod is resting**\n⏳ `{format_time(cooldown_left('fish', uid))}`", reply_markup=close_button(uid))
    
    set_cooldown("fish", uid)
    catches = [("🐟 Small Fish", 100, 400), ("🐠 Golden Fish", 500, 1500), ("🦈 Rare Catch", 1500, 5000), ("💎 Treasure Chest", 3000, 10000)]
    item, low, high = random.choice(catches)
    reward = random.randint(low, high)
    update_cash(uid, reward)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 🎣 **FISHING SUCCESS**\n"
        f"│\n"
        f"│ 🌊 Catch: **{item}**\n"
        f"│ 💰 Value: **+{money(reward)}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("hunt"))
async def hunt(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if cooldown_left("hunt", uid):
        return await m.reply_text(f"🏹 **Hunt is on cooldown**\n⏳ `{format_time(cooldown_left('hunt', uid))}`", reply_markup=close_button(uid))
    
    set_cooldown("hunt", uid)
    rewards = [("🐇 Rabbit", 200, 600), ("🦌 Deer", 500, 1800), ("🐗 Rare Find", 1000, 3000), ("💎 Ancient Treasure", 3000, 9000)]
    item, low, high = random.choice(rewards)
    reward = random.randint(low, high)
    update_cash(uid, reward)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 🏹 **HUNTING SUCCESS**\n"
        f"│\n"
        f"│ 🔎 Found: **{item}**\n"
        f"│ 💰 Reward: **+{money(reward)}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command(["inventory", "inv"]))
async def inventory(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    try:
        items = get_inventory(uid)
    except Exception:
        items = {}
        
    icons = {"fish": "🐟", "gem": "💎", "gold": "🪙", "diamond": "💠", "treasure": "💰", "shield": "🛡️", "key": "🔑"}
    
    text = f"{BOX_START}│ 🎒 **INVENTORY**\n│\n│ 👤 **{m.from_user.first_name}**\n{LINE_SEP}\n"
    
    if not items:
        text += "│ 📦 Inventory is empty.\n"
    elif isinstance(items, dict):
        for item, amount in items.items():
            icon = icons.get(str(item).lower(), "📦")
            text += f"│ {icon} **{item}** × `{amount}`\n"
    else:
        for item in items:
            text += f"│ 📦 **{item}**\n"
            
    text += BOX_END
    await m.reply_text(text, reply_markup=close_button(uid))

@bot.on_message(filters.command(["richlist", "leaderboard", "top"]))
async def richlist(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    
    rich = get_richlist()
    text = f"{BOX_START}│ 👑 **TOP 10 RICHEST**\n│\n"
    
    if not rich:
        text += "│ ❌ No players found.\n"
    else:
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for index, user in enumerate(rich[:10], 1):
            try:
                name = user.get("name", "Unknown")
                cash = user.get("cash", 0)
            except Exception:
                name, cash = "Unknown", 0
                
            medal = medals.get(index, f"#{index}")
            text += f"│ {medal} **{name}**\n│    💰 {money(cash)}\n"
            
    text += BOX_END
    await m.reply_text(text, reply_markup=close_button(m.from_user.id))

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
        name = data.get("name", m.from_user.first_name or "Unknown") if isinstance(data, dict) else (m.from_user.first_name or "Unknown")
    except Exception:
        name = m.from_user.first_name or "Unknown"
        
    total = cash + bank_money
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 👤 **PROFILE CARD**\n"
        f"│\n"
        f"│ 🪪 Name: **{name}**\n"
        f"{LINE_SEP}\n"
        f"│ 💵 Cash: **{money(cash)}**\n"
        f"│ 🏦 Bank: **{money(bank_money)}**\n"
        f"│ 💎 Net Worth: **{money(total)}**\n"
        f"{LINE_SEP}\n"
        f"│ ⚔️ Kills: **{kills_count}**\n"
        f"│ 🎮 Status: **ACTIVE**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

# ============================================================
# 🎮 TIC-TAC-TOE (PRO SMART AI)
# ============================================================

def check_winner(board):
    wins = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]
    for a,b,c in wins:
        if board[a] == board[b] == board[c] and board[a] != " ":
            return board[a]
    if " " not in board: return "Draw"
    return None

def get_xo_keyboard(game_id, board):
    keys = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            idx = i + j
            val = board[idx]
            if val == " ": btn_text = "⬜"
            elif val == "X": btn_text = "❌"
            else: btn_text = "⭕"
            row.append(InlineKeyboardButton(btn_text, callback_data=f"xo:{game_id}:{idx}"))
        keys.append(row)
    keys.append([InlineKeyboardButton("🏳️ Forfeit", callback_data=f"xo_forfeit:{game_id}")])
    return InlineKeyboardMarkup(keys)

def smart_bot_move(board):
    empty = [i for i, x in enumerate(board) if x == " "]
    if not empty: return None
    
    # 1. Try to Win
    for i in empty:
        board[i] = "O"
        if check_winner(board) == "O":
            board[i] = " "
            return i
        board[i] = " "
        
    # 2. Block Player
    for i in empty:
        board[i] = "X"
        if check_winner(board) == "X":
            board[i] = " "
            return i
        board[i] = " "
        
    # 3. Take Center
    if 4 in empty: return 4
    
    # 4. Take Corners
    corners = [x for x in [0, 2, 6, 8] if x in empty]
    if corners: return random.choice(corners)
    
    # 5. Random
    return random.choice(empty)

@bot.on_message(filters.command("xo"))
async def xo_start(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    player = m.from_user
    
    # PvP Mode
    if m.reply_to_message:
        opponent = m.reply_to_message.from_user
        if opponent.id == player.id: return await m.reply_text("❌ **You cannot play against yourself.**", reply_markup=close_button(player.id))
        if opponent.is_bot: return await m.reply_text("❌ **Bots cannot play PvP XO.**", reply_markup=close_button(player.id))
        
        await ensure_user(opponent)
        gid = f"pvp_{player.id}_{opponent.id}_{random.randint(1000,9999)}"
        
        xo_games[gid] = {
            "mode": "pvp", "p1": player.id, "p1_name": player.first_name or "Player 1",
            "p2": opponent.id, "p2_name": opponent.first_name or "Player 2",
            "board": [" "]*9, "turn": "X", "msg_id": None
        }
        
        msg = await m.reply_text(
            f"{BOX_START}"
            f"│ 🎮 **TIC-TAC-TOE (PvP)**\n"
            f"│\n"
            f"│ ❌ **{player.first_name}** vs ⭕ **{opponent.first_name}**\n"
            f"│\n"
            f"│ 🎯 Turn: **{player.first_name}** (❌)\n"
            f"{BOX_END}",
            reply_markup=get_xo_keyboard(gid, xo_games[gid]["board"])
        )
        xo_games[gid]["msg_id"] = msg.id
        return

    # Bot Mode
    gid = f"bot_{player.id}_{random.randint(1000,9999)}"
    xo_games[gid] = {
        "mode": "bot", "player": player.id, "p_name": player.first_name or "Player",
        "board": [" "]*9, "turn": "X", "msg_id": None
    }
    
    msg = await m.reply_text(
        f"{BOX_START}"
        f"│ 🤖 **TIC-TAC-TOE (vs Bot)**\n"
        f"│\n"
        f"│ 👤 You: ❌\n"
        f"│ 🤖 Bot: ⭕\n"
        f"│\n"
        f"│ 🎯 Your Turn!\n"
        f"{BOX_END}",
        reply_markup=get_xo_keyboard(gid, xo_games[gid]["board"])
    )
    xo_games[gid]["msg_id"] = msg.id

@bot.on_callback_query(filters.regex(r"^xo:"))
async def xo_callback(_, query):
    data = query.data.split(":")
    if len(data) != 3: return
    
    gid = data[1]
    try: pos = int(data[2])
    except: return
    
    game = xo_games.get(gid)
    if not game: return await query.answer("Game Over!", show_alert=True)
    
    uid = query.from_user.id
    
    # PvP Logic
    if game["mode"] == "pvp":
        if uid not in [game["p1"], game["p2"]]:
            return await query.answer("❌ Not your game!", show_alert=True)
        
        curr_turn = game["p1"] if game["turn"] == "X" else game["p2"]
        if uid != curr_turn:
            return await query.answer("⏳ Not your turn!", show_alert=True)
        if game["board"][pos] != " ":
            return await query.answer("❌ Box occupied!", show_alert=True)
            
        game["board"][pos] = game["turn"]
        winner = check_winner(game["board"])
        
        if winner:
            del xo_games[gid]
            w_name = "Draw" if winner == "Draw" else (game["p1_name"] if winner == "X" else game["p2_name"])
            txt = f"🏆 **Winner:** {w_name}" if winner != "Draw" else "🤝 **It's a Draw!**"
            return await query.message.edit_text(f"{BOX_START}│ 🎮 **GAME OVER**\n│\n│ {txt}\n{BOX_END}")
            
        game["turn"] = "O" if game["turn"] == "X" else "X"
        next_p = game["p1_name"] if game["turn"] == "X" else game["p2_name"]
        
        await query.message.edit_text(
            f"{BOX_START}"
            f"│ 🎮 **TIC-TAC-TOE (PvP)**\n"
            f"│\n"
            f"│ 🎯 Turn: **{next_p}** ({game['turn']})\n"
            f"{BOX_END}",
            reply_markup=get_xo_keyboard(gid, game["board"])
        )
        await query.answer("Move Played!")

    # Bot Logic
    else:
        if uid != game["player"]:
            return await query.answer("❌ Not your game!", show_alert=True)
        if game["turn"] != "X":
            return await query.answer("⏳ Wait for bot...", show_alert=True)
        if game["board"][pos] != " ":
            return await query.answer("❌ Box occupied!", show_alert=True)
            
        # Player Move
        game["board"][pos] = "X"
        if check_winner(game["board"]) == "X":
            del xo_games[gid]
            return await query.message.edit_text(f"{BOX_START}│ 🎉 **YOU WON!**\n│ You defeated the AI!\n{BOX_END}")
            
        # Bot Move
        game["turn"] = "O"
        bot_pos = smart_bot_move(game["board"])
        if bot_pos is not None:
            game["board"][bot_pos] = "O"
            
        if check_winner(game["board"]) == "O":
            del xo_games[gid]
            return await query.message.edit_text(f"{BOX_START}│ 🤖 **BOT WON!**\n│ Better luck next time.\n{BOX_END}")
        if check_winner(game["board"]) == "Draw":
            del xo_games[gid]
            return await query.message.edit_text(f"{BOX_START}│ 🤝 **DRAW!**\n│ No one won.\n{BOX_END}")
            
        game["turn"] = "X"
        await query.message.edit_text(
            f"{BOX_START}"
            f"│ 🤖 **TIC-TAC-TOE (vs Bot)**\n"
            f"│\n"
            f"│ 🎯 Your Turn! (❌)\n"
            f"{BOX_END}",
            reply_markup=get_xo_keyboard(gid, game["board"])
        )
        await query.answer("🤖 Bot moved!")

@bot.on_callback_query(filters.regex(r"^xo_forfeit:"))
async def xo_forfeit(_, query):
    gid = query.data.split(":")[1]
    game = xo_games.get(gid)
    if not game: return await query.answer("Game already ended.", show_alert=True)
    
    del xo_games[gid]
    await query.message.edit_text(f"{BOX_START}│ 🏳️ **GAME FORFEITED**\n│ You gave up!\n{BOX_END}")

@bot.on_message(filters.command("xogames"))
async def xo_games_list(_, m):
    await delete_command(m)
    count = len(xo_games)
    await m.reply_text(
        f"{BOX_START}"
        f"│ 🎮 **XO SERVER STATUS**\n"
        f"│\n"
        f"│ 🎯 Active Games: **{count}**\n"
        f"│ 🎮 Mode: **Tic-Tac-Toe**\n"
        f"│\n"
        f"│ 💡 Start: `/xo`\n"
        f"│ 👥 PvP: Reply to a player with `/xo`\n"
        f"{BOX_END}",
        reply_markup=close_button(m.from_user.id)
    )

# ============================================================
# 📜 HELP & UTILS
# ============================================================

@bot.on_message(filters.command(["gamehelp", "games"]))
async def game_help(_, m):
    await delete_command(m)
    await m.reply_text(
        f"{BOX_START}"
        f"│ 🎮 **AR WORLD COMMANDS**\n"
        f"{LINE_SEP}\n"
        f"│ 💰 **Economy:**\n"
        f"│ `/bal`, `/daily`, `/work`, `/beg`\n"
        f"│ `/deposit`, `/withdraw`, `/give`\n"
        f"│\n"
        f"│ ⚔️ **Action:**\n"
        f"│ `/kill`, `/rob`, `/roball`, `/crime`\n"
        f"│ `/protect`, `/shield`, `/kills`\n"
        f"│\n"
        f"│ 🎲 **Games:**\n"
        f"│ `/xo` (Smart AI), `/xogames`, `/flip`\n"
        f"│\n"
        f"│ 🌎 **Adventure:**\n"
        f"│ `/arworld`, `/mine`, `/fish`, `/hunt`\n"
        f"│\n"
        f"│ 📊 **Stats:**\n"
        f"│ `/profile`, `/richlist`, `/inventory`\n"
        f"{BOX_END}",
        reply_markup=close_button(m.from_user.id)
    )

@bot.on_callback_query(filters.regex(r"^close_"))
async def close_btn(_, query):
    try:
        uid = int(query.data.split("_")[1])
    except Exception:
        return await query.answer("Invalid button.", show_alert=True)
        
    if query.from_user.id != uid:
        return await query.answer("⚠️ Ye button aapka nahi hai!", show_alert=True)
        
    try:
        await query.message.delete()
    except Exception:
        try:
            await query.answer("Already closed.")
        except Exception:
            pass
