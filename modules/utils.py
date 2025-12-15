#*****************************
#utils.py   ver 04--
#*****************************

import datetime

def time_now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def duration_seconds(start, end):
    fmt = "%Y-%m-%d %H:%M:%S"
    s = datetime.datetime.strptime(start, fmt)
    e = datetime.datetime.strptime(end, fmt)
    return int((e - s).total_seconds())

def format_hhmm(seconds):
    if seconds is None: return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}"

