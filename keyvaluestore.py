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
    
    kv_cache = {} # we want most read requests to hit the cache
    
    def set(key, value):
        assert isinstance(key, str)
        assert isinstance(value, str) or value is None
        cur.execute("DELETE FROM keyvalue WHERE key = %s;", (key,))
        if key in kv_cache:
            del kv_cache[key]
        if value is not None:
            cur.execute("INSERT INTO keyvalue (key, value) VALUES (%s, %s);", (key, value))
            kv_cache[key] = value
        conn.commit()
    
    def get(key, default=None):
        assert isinstance(key, str)
        if key not in kv_cache:
            cur.execute("SELECT value FROM keyvalue WHERE key = %s;", (key,))
            result = cur.fetchone()
            if result:
                kv_cache[key] = result[0]
            else:
                kv_cache[key] = None
        
        ret = kv_cache[key]
        if ret is None:
            return default
        else:
            return ret
        
else:
    # we are running locally, use shelve
    import shelve
    s = shelve.open("devdata.db")
    
    def get(key, default=None):
        assert isinstance(key, str)
        if key in s:
            return s[key]
        else:
            return default
            
    def set(key, value):
        assert isinstance(key, str)
        assert isinstance(value, str) or value is None
        if key in s:
            del s[key]
        if value is not None:
            s[key] = value
