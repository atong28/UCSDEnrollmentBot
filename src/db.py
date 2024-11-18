import sqlite3
import json

def init_db():
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pid TEXT UNIQUE NOT NULL,
        discord_user_id TEXT UNIQUE NOT NULL,
        verified BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        json_data TEXT
    )
    ''')

    conn.commit()
    conn.close()

def link_pid(discord_user_id, pid):
    try:
        conn = sqlite3.connect('data/users.db')
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO users (discord_user_id, pid)
        VALUES (?, ?)
        ''', (discord_user_id, pid))

        conn.commit()
        print(f"Discord User {discord_user_id} linked with PID {pid}!")
    except sqlite3.IntegrityError as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def get_user(discord_user_id=None, pid=None):
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()
    
    if discord_user_id:
        cursor.execute('SELECT * FROM users WHERE discord_user_id = ?', (discord_user_id,))
    elif pid:
        cursor.execute('SELECT * FROM users WHERE pid = ?', (pid,))
    
    user = cursor.fetchone()
    conn.close()
    return user

def delete_user(discord_user_id: int) -> None:
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE discord_user_id = ?', (discord_user_id,))
    conn.commit()
    conn.close()

def check_user_exists(discord_user_id: int):
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()

    cursor.execute('SELECT verified FROM users WHERE discord_user_id = ?', (discord_user_id,))
    user = cursor.fetchone()
    conn.close()
    return True if user else False

def check_user_verified(discord_user_id: int):
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()

    cursor.execute('SELECT verified FROM users WHERE discord_user_id = ?', (discord_user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return user[0] == 1
    return False

def insert_or_update_user(pid, json_data):
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()

    json_string = json.dumps(json_data)
    cursor.execute('SELECT verified FROM users WHERE pid = ?', (pid,))
    user = cursor.fetchone()

    if user:
        cursor.execute('''
        UPDATE users 
        SET json_data = ?, verified = 1 
        WHERE pid = ?
        ''', (json_string, pid))

    conn.commit()
    conn.close()

def get_json_data(discord_user_id):
    conn = sqlite3.connect('data/users.db')
    cursor = conn.cursor()

    # Query to retrieve the json_data for the given discord_user_id
    cursor.execute('SELECT json_data FROM users WHERE discord_user_id = ?', (discord_user_id,))
    result = cursor.fetchone()

    if result:
        json_data_str = result[0]
        try:
            json_data = json.loads(json_data_str)
            return json_data
        except:
            return None
    else:
        return None