import random

# https://stackoverflow.com/questions/1181919/python-base-36-encoding
def base36encode(number, alphabet='0123456789abcdefghijklmnopqrstuvwxyz'):
    """Converts an integer to a base36 string."""
    base36 = ''
    sign = ''

    if number < 0:
        sign = '-'
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36

pw_history = []     # ensures that no two passwords for one instance are the same
PW_HISTORY_SIZE = 5 # number of passwords generated per instance
def makepw():
    while True:
        pw = base36encode(random.randint(1, int("zzzz", 36)))
        if pw not in pw_history:
            break
    pw_history.append(pw)
    while len(pw_history) > PW_HISTORY_SIZE:
        del pw_history[0]
    return pw

