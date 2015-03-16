from flask import g
from datetime import datetime

def send_query(db, query):
    cur = db.cursor()
    cur.execute(query)
    return cur

def get_gps_utc_constants():
    leap_seconds_result = send_query(g.eor_db,
        "SELECT leap_seconds FROM leap_seconds ORDER BY leap_seconds DESC LIMIT 1").fetchone()

    leap_seconds = leap_seconds_result[0]

    GPS_LEAP_SECONDS_OFFSET = leap_seconds - 19

    jan_1_1970 = datetime(1970, 1, 1)

    jan_6_1980 = datetime(1980, 1, 6)

    GPS_UTC_DELTA = (jan_6_1980 - jan_1_1970).total_seconds()

    return (GPS_LEAP_SECONDS_OFFSET, GPS_UTC_DELTA)
