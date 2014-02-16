import os

if os.environ.get("DATABASE_URL"):
    # we are running on heroku, use postgres
    import psycopg2
    import urllib.parse
    
    urllib.parse.uses_netloc.append("postgres")
    url = urllib.parse.urlparse(os.environ["DATABASE_URL"])
    
    conn = psycopg2.connect(
        database = url.path[1:],
        user = url.username,
        password = url.password,
        host = url.hostname,
        port = url.port
    )
    
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS keyvalue (key varchar primary key, value varchar);")
    
    def set(key, value):
        cur.execute("DELETE FROM keyvalue WHERE key = %s;", (key,))
        if value is not None:
            cur.execute("INSERT INTO keyvalue (key, value) VALUES (%s, %s);", (key, value))
    
    def get(key):
        cur.execute("SELECT value FROM keyvalue WHERE key = %s;", (key,))
        result = cur.fetchone()
        if result:
            return result[0]
        else:
            return None
        
else:
    # we are running locally, use shelve
    import shelve
    s = shelve.open("devdata.db")
    
    def get(key, default=None):
        if key in s:
            return s[key]
        else:
            return default
            
    def set(key, value):
        s[key] = value
