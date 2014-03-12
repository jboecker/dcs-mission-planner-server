import sqlite3
conn = sqlite3.connect("data.sqlite3")

conn.execute("CREATE TABLE IF NOT EXISTS data (key text, value text);")
conn.commit()

def get(key, default=None):
    assert isinstance(key, str)
    cur = conn.cursor()
    cur.execute("SELECT value FROM data WHERE key = ?", (key,))
    result = cur.fetchone()
    if result is None:
        return default
    else:
        return result[0]

def set(key, value):
    assert isinstance(key, str)
    assert isinstance(value, str) or value is None
    cur = conn.cursor()
    cur.execute("DELETE FROM data WHERE key = ?", (key,))
    cur.execute("INSERT INTO data (key, value) VALUES (?, ?)", (key, value))
    conn.commit()

def as_dict():
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM data")
    return dict(cur.fetchall())
