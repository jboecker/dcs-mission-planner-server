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
        s.sync()
