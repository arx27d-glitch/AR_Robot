# ============================================================
#                    AR WORLD DATABASE HANDLER
#                  ADVANCED SQLITE INTEGRATION
# ============================================================

import sqlite3
import json
import os
from datetime import datetime

# Database Path (Auto-create in root or specific folder)
DB_PATH = "arworld_game.db"

def get_connection():
    """Get database connection with Row factory for dict-like access"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize Database Tables if not exists"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users Table: Stores basic info, cash, bank, kills, name
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT DEFAULT 'Unknown',
            cash INTEGER DEFAULT 0,
            bank INTEGER DEFAULT 0,
            kills INTEGER DEFAULT 0,
            protection_expiry TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Inventory Table: Stores items as JSON string
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER PRIMARY KEY,
            items TEXT DEFAULT '{}',
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()

# ============================================================
# USER MANAGEMENT
# ============================================================

async def register_user(user_id):
    """Register a new user if not exists"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        cursor.execute("INSERT OR IGNORE INTO inventory (user_id) VALUES (?)", (user_id,))
        conn.commit()
    except Exception as e:
        print(f"DB Error in register_user: {e}")
    finally:
        conn.close()

async def update_name(user_id, name):
    """Update user's display name"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (name, user_id))
        conn.commit()
    except Exception as e:
        print(f"DB Error in update_name: {e}")
    finally:
        conn.close()

async def get_profile(user_id):
    """Get full user profile data"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"DB Error in get_profile: {e}")
        return None
    finally:
        conn.close()

# ============================================================
# ECONOMY (CASH & BANK)
# ============================================================

async def get_cash(user_id):
    """Get user's cash balance"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT cash FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row['cash'] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()

async def update_cash(user_id, amount):
    """Add or subtract cash (amount can be negative)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Ensure balance doesn't go below 0 if subtracting
        if amount < 0:
            current = await get_cash(user_id)
            if current + amount < 0:
                amount = -current # Set to 0 instead of negative
        
        cursor.execute("UPDATE users SET cash = cash + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
    except Exception as e:
        print(f"DB Error in update_cash: {e}")
    finally:
        conn.close()

async def get_bank(user_id):
    """Get user's bank balance"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT bank FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row['bank'] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()

async def add_bank(user_id, amount):
    """Add money to bank"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET bank = bank + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
    except Exception as e:
        print(f"DB Error in add_bank: {e}")
    finally:
        conn.close()

async def remove_bank(user_id, amount):
    """Remove money from bank"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET bank = bank - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
    except Exception as e:
        print(f"DB Error in remove_bank: {e}")
    finally:
        conn.close()

async def update_bank(user_id, amount):
    """Alias for add_bank to match game.py calls"""
    await add_bank(user_id, amount)

# ============================================================
# STATS (KILLS)
# ============================================================

async def get_kills(user_id):
    """Get total kills"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT kills FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row['kills'] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()

async def update_kills(user_id, amount=1):
    """Increment kills"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET kills = kills + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
    except Exception as e:
        print(f"DB Error in update_kills: {e}")
    finally:
        conn.close()

# ============================================================
# PROTECTION (SHIELD)
# ============================================================

async def set_protection(user_id, expiry_datetime):
    """Set protection expiry date"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        expiry_str = expiry_datetime.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET protection_expiry = ? WHERE user_id = ?", (expiry_str, user_id))
        conn.commit()
    except Exception as e:
        print(f"DB Error in set_protection: {e}")
    finally:
        conn.close()

async def get_protection(user_id):
    """Check if user has active protection. Returns expiry string or None"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT protection_expiry FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row or not row['protection_expiry']:
            return None
            
        expiry_str = row['protection_expiry']
        expiry_dt = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
        
        if datetime.now() < expiry_dt:
            return expiry_str # Active
        else:
            # Expired, clear it
            cursor.execute("UPDATE users SET protection_expiry = NULL WHERE user_id = ?", (user_id,))
            conn.commit()
            return None
    except Exception as e:
        print(f"DB Error in get_protection: {e}")
        return None
    finally:
        conn.close()

# ============================================================
# LEADERBOARD
# ============================================================

async def get_richlist():
    """Get top 10 richest players by Total Wealth (Cash + Bank)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Order by sum of cash and bank descending
        cursor.execute("""
            SELECT user_id, name, cash, bank 
            FROM users 
            ORDER BY (cash + bank) DESC 
            LIMIT 10
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"DB Error in get_richlist: {e}")
        return []
    finally:
        conn.close()

# ============================================================
# INVENTORY SYSTEM
# ============================================================

async def get_inventory(user_id):
    """Get user inventory as a dictionary"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT items FROM inventory WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row and row['items']:
            return json.loads(row['items'])
        return {}
    except Exception as e:
        print(f"DB Error in get_inventory: {e}")
        return {}
    finally:
        conn.close()

async def add_item(user_id, item_name, quantity=1):
    """Add an item to user's inventory"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get current inventory
        cursor.execute("SELECT items FROM inventory WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        current_items = {}
        if row and row['items']:
            current_items = json.loads(row['items'])
            
        # Update quantity
        current_items[item_name] = current_items.get(item_name, 0) + quantity
        
        # Save back
        cursor.execute("UPDATE inventory SET items = ? WHERE user_id = ?", (json.dumps(current_items), user_id))
        conn.commit()
    except Exception as e:
        print(f"DB Error in add_item: {e}")
    finally:
        conn.close()

async def remove_item(user_id, item_name, quantity=1):
    """Remove an item from user's inventory"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT items FROM inventory WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row or not row['items']:
            return False
            
        current_items = json.loads(row['items'])
        
        if item_name in current_items:
            current_items[item_name] -= quantity
            if current_items[item_name] <= 0:
                del current_items[item_name]
                
            cursor.execute("UPDATE inventory SET items = ? WHERE user_id = ?", (json.dumps(current_items), user_id))
            conn.commit()
            return True
        return False
    except Exception as e:
        print(f"DB Error in remove_item: {e}")
        return False
    finally:
        conn.close()

async def has_item(user_id, item_name):
    """Check if user has a specific item"""
    inv = await get_inventory(user_id)
    return item_name in inv and inv[item_name] > 0
