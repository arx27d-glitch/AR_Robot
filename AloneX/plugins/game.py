# ============================================================
#                    AR WORLD PRO GAME BOT
#                  ADVANCED GAME.PY (V2.0)
# ============================================================

import random
import time
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

# Styling Constants
BOX_START = "╭━━━〔 🌟 AR WORLD PRO 〕━━━╮\n│\n"
BOX_END = "│\n╰━━━━━━━━━━━━━━━━━━━━━━╯"
LINE_SEP = "├──────────────────────"

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
        amount = int(value.replace(',', ''))
        return amount if amount > 0 else None
    except Exception:
        return None

def now_ts():
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
    
    # Bonus Logic
    bonus_txt = ""
    if random.randint(1, 100) <= 10:
        bonus = random.randint(3000, 7000)
        reward += bonus
        bonus_txt = f"│ 🔥 **Lucky Bonus:** +{money(bonus)}\n"
    
    locations = ["🏙️ Neon City", "🌲 Dark Forest", "🏜️ Lost Desert", "🏝️ Mystery Island", "🏰 Ancient Castle"]
    
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
        f"├──────────────────────\n"
        f"│ 💵 **Cash:** {money(cash)}\n"
        f"│ 🏦 **Bank:** {money(bank)}\n"
        f"├──────────────────────\n"
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
    
    jobs = [("💻 Coder", 500, 2500), ("🎨 Designer", 400, 2200), ("🚕 Driver", 500, 2500), ("🍕 Delivery", 300, 1800)]
    job, low, high = random.choice(jobs)
    reward = random.randint(low, high)
    
    update_cash(uid, reward)
    set_cooldown("work", uid)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 💼 **Work Complete**\n"
        f"│ Job: {job}\n"
        f"│ Earned: **+{money(reward)}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("crime"))
async def crime(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    if cooldown_left("crime", uid):
        return await m.reply_text(f"🚨 **Cooldown:** `{format_time(cooldown_left('crime', uid))}`", reply_markup=close_button(uid))
    
    set_cooldown("crime", uid)
    
    if random.randint(1, 100) <= 65:
        reward = random.randint(500, 4000)
        update_cash(uid, reward)
        await m.reply_text(
            f"{BOX_START}"
            f"│ 🚨 **Crime Successful!**\n"
            f"│ You escaped with loot.\n"
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

# ============================================================
# ⚔️ KILL & ROB SYSTEM (ADVANCED)
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
    
    # Check Protection
    if get_protection(victim.id):
        return await m.reply_text(
            f"{BOX_START}"
            f"│ 🛡️ **Protected Target**\n"
            f"│ {victim.first_name} has an active shield.\n"
            f"│ ❌ Attack Blocked!\n"
            f"{BOX_END}", reply_markup=close_button(uid)
        )

    # Animation Message
    anim_msg = await m.reply_text(f"⚔️ **{attacker.first_name}** is attacking **{victim.first_name}**...")
    time.sleep(1.5) # Fake delay for effect
    
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
        return await m.reply_text(f"⏳ **Rob Cooldown:** `{format_time(cooldown_left('rob', uid))}`", reply_markup=close_button(uid))
    
    set_cooldown("rob", uid)
    
    if get_protection(victim.id):
        return await m.reply_text(f"🛡️ **{victim.first_name}** is protected by a Shield!", reply_markup=close_button(uid))
    
    victim_cash = get_cash(victim.id)
    if victim_cash <= 0:
        return await m.reply_text("💸 **Target is broke!** Nothing to rob.", reply_markup=close_button(uid))
    
    # Success Chance 60%
    if random.randint(1, 100) <= 60:
        amount = random.randint(max(1, int(victim_cash * 0.10)), max(1, int(victim_cash * 0.35)))
        amount = min(amount, victim_cash)
        
        update_cash(victim.id, -amount)
        update_cash(uid, amount)
        
        await m.reply_text(
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
        
        await m.reply_text(
            f"{BOX_START}"
            f"│ 🚔 **ROBBERY FAILED**\n"
            f"│\n"
            f"│ ❌ You were caught!\n"
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
        f"│ 🔒 Expires: `{expires.strftime('%d-%m %H:%M')}`\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

# ============================================================
# 🎮 TIC-TAC-TOE (PRO VERSION)
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
            if val == " ":
                btn_text = "⬜"
            elif val == "X":
                btn_text = "❌"
            else:
                btn_text = "⭕"
            
            row.append(InlineKeyboardButton(btn_text, callback_data=f"xo:{game_id}:{idx}"))
        keys.append(row)
    
    keys.append([InlineKeyboardButton("🏳️ Forfeit", callback_data=f"xo_forfeit:{game_id}")])
    return InlineKeyboardMarkup(keys)

def smart_bot_move(board):
    empty = [i for i, x in enumerate(board) if x == " "]
    
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
    
    # 4. Random
    return random.choice(empty)

@bot.on_message(filters.command("xo"))
async def xo_start(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    player = m.from_user
    
    # PvP Mode
    if m.reply_to_message:
        opponent = m.reply_to_message.from_user
        if opponent.id == player.id: return await m.reply_text("❌ Can't play with yourself.")
        if opponent.is_bot: return await m.reply_text("❌ Bots can't play PvP.")
        
        await ensure_user(opponent)
        gid = f"pvp_{player.id}_{opponent.id}_{random.randint(1000,9999)}"
        
        xo_games[gid] = {
            "mode": "pvp",
            "p1": player.id, "p1_name": player.first_name,
            "p2": opponent.id, "p2_name": opponent.first_name,
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
        "mode": "bot",
        "player": player.id, "p_name": player.first_name,
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
            return await query.message.edit_text(
                f"{BOX_START}│ 🎮 **GAME OVER**\n│\n│ {txt}\n{BOX_END}"
            )
            
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
        
        # Check Player Win
        if check_winner(game["board"]) == "X":
            del xo_games[gid]
            return await query.message.edit_text(
                f"{BOX_START}│ 🎉 **YOU WON!**\n│ You defeated the AI!\n{BOX_END}"
            )
            
        # Bot Move
        game["turn"] = "O"
        bot_pos = smart_bot_move(game["board"])
        game["board"][bot_pos] = "O"
        
        # Check Bot Win
        if check_winner(game["board"]) == "O":
            del xo_games[gid]
            return await query.message.edit_text(
                f"{BOX_START}│ 🤖 **BOT WON!**\n│ Better luck next time.\n{BOX_END}"
            )
            
        # Check Draw
        if check_winner(game["board"]) == "Draw":
            del xo_games[gid]
            return await query.message.edit_text(
                f"{BOX_START}│ 🤝 **DRAW!**\n│ No one won.\n{BOX_END}"
            )
            
        game["turn"] = "X"
        await query.message.edit_text(
            f"{BOX_START}"
            f"│ 🤖 **TIC-TAC-TOE (vs Bot)**\n"
            f"│\n"
            f"│ 🎯 Your Turn! (❌)\n"
            f"{BOX_END}",
            reply_markup=get_xo_keyboard(gid, game["board"])
        )
        await query.answer("Bot moved!")

@bot.on_callback_query(filters.regex(r"^xo_forfeit:"))
async def xo_forfeit(_, query):
    gid = query.data.split(":")[1]
    game = xo_games.get(gid)
    if not game: return
    
    del xo_games[gid]
    await query.message.edit_text(
        f"{BOX_START}│ 🏳️ **GAME FORFEITED**\n│ You gave up!\n{BOX_END}"
    )

# ============================================================
# 📊 STATS & UTILS
# ============================================================

@bot.on_message(filters.command(["profile", "me"]))
async def profile(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    uid = m.from_user.id
    
    cash = get_cash(uid)
    bank = get_bank(uid)
    kills = get_kills(uid)
    
    await m.reply_text(
        f"{BOX_START}"
        f"│ 👤 **PROFILE CARD**\n"
        f"├──────────────────────\n"
        f"│ 🆔 Name: **{m.from_user.first_name}**\n"
        f"│ 💵 Cash: **{money(cash)}**\n"
        f"│ 🏦 Bank: **{money(bank)}**\n"
        f"│ 💎 Net: **{money(cash+bank)}**\n"
        f"├──────────────────────\n"
        f"│ ⚔️ Kills: **{kills}**\n"
        f"│ 🛡️ Shield: **{'Active' if get_protection(uid) else 'Inactive'}**\n"
        f"{BOX_END}",
        reply_markup=close_button(uid)
    )

@bot.on_message(filters.command("richlist"))
async def richlist(_, m):
    await delete_command(m)
    await ensure_user(m.from_user)
    
    users = get_richlist()[:10]
    text = f"{BOX_START}│ 👑 **TOP 10 RICHEST**\n│\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(users):
        medal = medals[i] if i < 3 else f"#{i+1}"
        name = u.get("name", "Unknown")
        cash = u.get("cash", 0)
        text += f"│ {medal} **{name}**: {money(cash)}\n"
        
    text += BOX_END
    await m.reply_text(text, reply_markup=close_button(m.from_user.id))

@bot.on_callback_query(filters.regex(r"^close_"))
async def close_btn(_, query):
    uid = int(query.data.split("_")[1])
    if query.from_user.id != uid:
        return await query.answer("⚠️ This button is not for you!", show_alert=True)
    try:
        await query.message.delete()
    except:
        pass

# ============================================================
# HELP MENU
# ============================================================

@bot.on_message(filters.command(["gamehelp", "games"]))
async def game_help(_, m):
    await delete_command(m)
    await m.reply_text(
        f"{BOX_START}"
        f"│ 🎮 **AR WORLD COMMANDS**\n"
        f"├──────────────────────\n"
        f"│ 💰 **Economy:**\n"
        f"│ `/bal`, `/daily`, `/work`, `/beg`\n"
        f"│ `/deposit`, `/withdraw`, `/give`\n"
        f"│\n"
        f"│ ⚔️ **Action:**\n"
        f"│ `/kill`, `/rob`, `/crime`\n"
        f"│ `/protect`, `/shield`\n"
        f"│\n"
        f"│ 🎲 **Games:**\n"
        f"│ `/xo` (TicTacToe), `/flip`\n"
        f"│ `/arworld`, `/mine`, `/fish`\n"
        f"│\n"
        f"│ 📊 **Stats:**\n"
        f"│ `/profile`, `/richlist`, `/kills`\n"
        f"{BOX_END}",
        reply_markup=close_button(m.from_user.id)
    )
