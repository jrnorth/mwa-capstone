from flask import g
from datetime import datetime
from requests_futures.sessions import FuturesSession
from app import models
import psycopg2
import os

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

def get_gps_from_datetime(start_datetime, end_datetime):
    session = FuturesSession()

    baseUTCToGPSURL = 'http://ngas01.ivec.org/metadata/tconv/?utciso='

    requestURLStart = baseUTCToGPSURL + start_datetime.strftime('%Y-%m-%dT%H:%M:%S')

    requestURLEnd = baseUTCToGPSURL + end_datetime.strftime('%Y-%m-%dT%H:%M:%S')

    #Start the first Web service request in the background.
    future_start = session.get(requestURLStart)

    #The second request is started immediately.
    future_end = session.get(requestURLEnd)

    #Wait for the first request to complete, if it hasn't already.
    start_gps = int(future_start.result().content)

    #Wait for the second request to complete, if it hasn't already.
    end_gps = int(future_end.result().content)

    return (start_gps, end_gps)

def get_datetime_from_gps(start_gps, end_gps):
    session = FuturesSession()

    baseUTCToGPSURL = 'http://ngas01.ivec.org/metadata/tconv/?gpssec='

    requestURLStart = baseUTCToGPSURL + str(start_gps)

    requestURLEnd = baseUTCToGPSURL + str(end_gps)

    #Start the first Web service request in the background.
    future_start = session.get(requestURLStart)

    #The second request is started immediately.
    future_end = session.get(requestURLEnd)

    #Wait for the first request to complete, if it hasn't already.
    start_datetime = datetime.strptime(future_start.result().content.decode('utf-8'), '"%Y-%m-%dT%H:%M:%S"')

    #Wait for the second request to complete, if it hasn't already.
    end_datetime = datetime.strptime(future_end.result().content.decode('utf-8'), '"%Y-%m-%dT%H:%M:%S"')

    return (start_datetime, end_datetime)

def build_query(data_source):
    query = "SELECT "

    query += data_source.obs_column

    columns = models.GraphDataSourceColumn.query.filter(
        models.GraphDataSourceColumn.graph_data_source == data_source.name).all()

    for column in columns:
        query += ", " + column.name

    query += " FROM " + data_source.table
    query += " WHERE "

    query += data_source.obs_column + " >= {} AND "
    query += data_source.obs_column + " <= {} "

    query += " AND projectid='G0009' " if data_source.projectid else ""

    query += " ORDER BY " + data_source.obs_column + " ASC"

    return (query, columns)

def get_graph_data(data_source_str, start_gps, end_gps):
    data_source = models.GraphDataSource.query.filter(models.GraphDataSource.name == data_source_str).first()

    query, columns = build_query(data_source)

    db_conn = psycopg2.connect(database=data_source.database, host=data_source.host,
        user=os.environ['MWA_DB_USERNAME'], password=os.environ['MWA_DB_PW'])

    results = send_query(db_conn, query.format(start_gps, end_gps)).fetchall()

    db_conn.close()

    # Initialize empty data structure
    data = {}
    for column in columns:
        data[column.name] = []

    GPS_LEAP_SECONDS_OFFSET, GPS_UTC_DELTA = get_gps_utc_constants()

    for row in results:
                            # Actual UTC time of the observation (for the graph)
        utc_millis = int((row[0] - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000)
        for column_index in range(1, len(row) - 1): # Each row is a tuple that has an empty element at the end.
            if row[column_index] is not None:
                data[columns[column_index - 1].name].append([utc_millis, row[column_index]])

    return data
