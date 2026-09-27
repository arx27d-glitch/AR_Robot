from AloneX import database2 as database
from datetime import datetime


# =========================================================
# DATABASE
# =========================================================

db = database["game"]


# =========================================================
# USER / REGISTRATION
# =========================================================

async def register_user(user_id: int, name: str = None):
    user = await db.find_one({"user_id": user_id})

    if not user:
        await db.insert_one({
            "user_id": user_id,
            "name": name or "Unknown",

            # Economy
            "cash": 500,
            "bank": 0,

            # Stats
            "kills": 0,

            # Protection
            "protection": None,

            # Cooldowns
            "daily": 0,
            "work": 0,
            "crime": 0,

            # Rob / Steal
            "users": {},

            # Inventory
            "inventory": {}
        })

    elif name:
        await db.update_one(
            {"user_id": user_id},
            {"$set": {"name": name}}
        )

    return True


async def get_user(user_id: int):
    return await db.find_one({"user_id": user_id})


async def delete_data(user_id: int) -> bool:
    await db.delete_one({"user_id": user_id})
    return True


# =========================================================
# NAME
# =========================================================

async def update_name(user_id: int, name: str) -> bool:
    await db.update_one(
        {"user_id": user_id},
        {"$set": {"name": name}},
        upsert=True
    )
    return True


# =========================================================
# CASH / MONEY
# =========================================================

async def get_cash(user_id: int) -> int:
    user = await db.find_one({"user_id": user_id})

    if not user:
        return 0

    return user.get("cash", 0)


async def update_cash(user_id: int, cash: int = 0) -> bool:
    await db.update_one(
        {"user_id": user_id},
        {"$inc": {"cash": cash}},
        upsert=True
    )
    return True


# =========================================================
# BANK
# =========================================================

async def get_bank(user_id: int) -> int:
    user = await db.find_one({"user_id": user_id})

    if not user:
        return 0

    return user.get("bank", 0)


async def update_bank(user_id: int, amount: int) -> bool:
    await db.update_one(
        {"user_id": user_id},
        {"$inc": {"bank": amount}},
        upsert=True
    )
    return True


async def add_bank(user_id: int, amount: int) -> bool:
    return await update_bank(user_id, amount)


async def remove_bank(user_id: int, amount: int) -> bool:
    await db.update_one(
        {"user_id": user_id},
        {"$inc": {"bank": -amount}},
        upsert=True
    )
    return True


# =========================================================
# KILLS
# =========================================================

async def update_kills(user_id: int) -> bool:
    await db.update_one(
        {"user_id": user_id},
        {"$inc": {"kills": 1}},
        upsert=True
    )
    return True


async def get_kills(user_id: int) -> int:
    user = await db.find_one({"user_id": user_id})

    if not user:
        return 0

    return user.get("kills", 0)


# =========================================================
# PROTECTION / SHIELD
# =========================================================

async def set_protection(user_id: int, expiry) -> bool:
    await db.update_one(
        {"user_id": user_id},
        {"$set": {"protection": expiry}},
        upsert=True
    )
    return True


async def get_protection(user_id: int):
    user = await db.find_one({"user_id": user_id})

    if not user:
        return None

    return user.get("protection")


# =========================================================
# DAILY
# =========================================================

async def get_daily(user_id: int) -> int:
    user = await db.find_one({"user_id": user_id})

    if not user:
        return 0

    return user.get("daily", 0)


async def update_daily(user_id: int, timestamp: int) -> bool:
    await db.update_one(
        {"user_id": user_id},
        {"$set": {"daily": timestamp}},
        upsert=True
    )
    return True


# =========================================================
# WORK
# =========================================================

async def get_work(user_id: int) -> int:
    user = await db.find_one({"user_id": user_id})

    if not user:
        return 0

    return user.get("work", 0)


async def update_work(user_id: int, timestamp: int) -> bool:
    await db.update_one(
        {"user_id": user_id},
        {"$set": {"work": timestamp}},
        upsert=True
    )
    return True


# =========================================================
# CRIME
# =========================================================

async def get_crime(user_id: int) -> int:
    user = await db.find_one({"user_id": user_id})

    if not user:
        return 0

    return user.get("crime", 0)


async def update_crime(user_id: int, timestamp: int) -> bool:
    await db.update_one(
        {"user_id": user_id},
        {"$set": {"crime": timestamp}},
        upsert=True
    )
    return True


# =========================================================
# ROB / STEAL COOLDOWN
# =========================================================

async def get_steal_date(
    user_id: int,
    target_user_id: int
):
    user = await db.find_one(
        {"user_id": user_id}
    )

    if not user:
        return None

    users = user.get("users", {})

    return users.get(str(target_user_id))


async def update_steal_date(
    user_id: int,
    target_user_id: int,
    steal_date: int
) -> bool:

    await db.update_one(
        {"user_id": user_id},
        {
            "$set": {
                f"users.{target_user_id}": steal_date
            }
        },
        upsert=True
    )

    return True


# =========================================================
# PROFILE
# =========================================================

async def get_profile(user_id: int):
    user = await db.find_one(
        {"user_id": user_id}
    )

    if not user:
        return None

    return {
        "name": user.get("name", "Unknown"),
        "cash": user.get("cash", 0),
        "bank": user.get("bank", 0),
        "kills": user.get("kills", 0),
        "protection": user.get("protection"),
        "inventory": user.get("inventory", {})
    }


# =========================================================
# RICHLIST
# =========================================================

async def get_richlist(limit: int = 10):

    users = await db.find(
        {}
    ).sort(
        "cash",
        -1
    ).limit(
        limit
    ).to_list(
        length=limit
    )

    return users


async def get_top_users(limit: int = 10):
    return await get_richlist(limit)


# =========================================================
# INVENTORY
# =========================================================

async def add_item(
    user_id: int,
    item: str,
    amount: int = 1
) -> bool:

    await db.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                f"inventory.{item}": amount
            }
        },
        upsert=True
    )

    return True


async def remove_item(
    user_id: int,
    item: str,
    amount: int = 1
) -> bool:

    user = await db.find_one(
        {"user_id": user_id}
    )

    if not user:
        return False

    inventory = user.get(
        "inventory",
        {}
    )

    current = inventory.get(
        item,
        0
    )

    if current < amount:
        return False

    await db.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                f"inventory.{item}": -amount
            }
        }
    )

    return True


async def get_inventory(user_id: int):

    user = await db.find_one(
        {"user_id": user_id}
    )

    if not user:
        return {}

    return user.get(
        "inventory",
        {}
    )


async def has_item(
    user_id: int,
    item: str
):

    inventory = await get_inventory(
        user_id
    )

    return inventory.get(
        item,
        0
    )


# =========================================================
# TIC TAC TOE
# =========================================================

async def create_ttt(
    game_id,
    player1,
    player2="bot"
):

    await db.update_one(
        {"game_id": game_id},
        {
            "$set": {
                "game_id": game_id,

                "player1": player1,
                "player2": player2,

                "board": [
                    "⬜",
                    "⬜",
                    "⬜",
                    "⬜",
                    "⬜",
                    "⬜",
                    "⬜",
                    "⬜",
                    "⬜"
                ],

                "turn": player1,
                "status": "playing",
                "winner": None
            }
        },
        upsert=True
    )

    return True


async def get_ttt(game_id):

    return await db.find_one(
        {"game_id": game_id}
    )


async def update_ttt(
    game_id,
    board,
    turn
):

    await db.update_one(
        {"game_id": game_id},
        {
            "$set": {
                "board": board,
                "turn": turn
            }
        }
    )

    return True


async def end_ttt(
    game_id,
    winner
):

    await db.update_one(
        {"game_id": game_id},
        {
            "$set": {
                "status": "ended",
                "winner": winner
            }
        }
    )

    return True


async def delete_ttt(game_id):

    await db.delete_one(
        {"game_id": game_id}
    )

    return True


# =========================================================
# OPTIONAL GAME STATS
# =========================================================

async def get_stat(
    user_id: int,
    stat: str,
    default=0
):

    user = await db.find_one(
        {"user_id": user_id}
    )

    if not user:
        return default

    return user.get(
        stat,
        default
    )


async def set_stat(
    user_id: int,
    stat: str,
    value
):

    await db.update_one(
        {"user_id": user_id},
        {
            "$set": {
                stat: value
            }
        },
        upsert=True
    )

    return True


async def increment_stat(
    user_id: int,
    stat: str,
    amount: int = 1
):

    await db.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                stat: amount
            }
        },
        upsert=True
    )

    return True
