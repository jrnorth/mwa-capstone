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

def get_graph_data(data_source_str, start_gps, end_gps, the_set):
    data_source = models.GraphDataSource.query.filter(models.GraphDataSource.name == data_source_str).first()

    query, columns = build_query(data_source)

    db_conn = psycopg2.connect(database=data_source.database, host=data_source.host,
        user=os.environ['MWA_DB_USERNAME'], password=os.environ['MWA_DB_PW'])

    results = send_query(db_conn, query.format(start_gps, end_gps)).fetchall()

    db_conn.close()

    data = {}

    if the_set is not None:
        # Initialize empty data structure
        for column in columns:
            data[column.name] = []

        GPS_LEAP_SECONDS_OFFSET, GPS_UTC_DELTA = get_gps_utc_constants()

        results = join_with_obsids_from_set(results, the_set, data_source)

        for row in results:
                                # Actual UTC time of the observation (for the graph)
            utc_millis = int((row[0] - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000)
            for column_index in range(1, len(row)):
                if row[column_index] is not None:
                    data[columns[column_index - 1].name].append([utc_millis, row[column_index]])
    else: #No set, so we need to separate the data into sets for low/high and EOR0/EOR1
        data = separate_data_into_sets(data, results, columns, data_source, start_gps, end_gps)

    return data

def separate_data_into_sets(data, data_source_results, columns, data_source, start_gps, end_gps):
    projectid_clause = "AND projectid='G0009'" if data_source.projectid else ""
    obsid_results = send_query(g.eor_db, """SELECT starttime, obsname, ra_phase_center
                                    FROM mwa_setting
                                    WHERE starttime >= {} AND starttime <= {}
                                    {}
                                    AND (obsname LIKE 'low%' OR obsname LIKE 'high%')
                                    AND (ra_phase_center = 0 OR ra_phase_center = 60)
                                    ORDER BY starttime ASC""".format(start_gps,
                                    end_gps, projectid_clause)).fetchall()

    data['l0'] = {}
    data['l1'] = {}
    data['h0'] = {}
    data['h1'] = {}

    for key in data:
        for column in columns:
            data[key][column.name] = []

    data['utc_obsid_map_l0'] = []
    data['utc_obsid_map_l1'] = []
    data['utc_obsid_map_h0'] = []
    data['utc_obsid_map_h1'] = []

    all_obsids = [obsid_tuple[0] for obsid_tuple in obsid_results]

    GPS_LEAP_SECONDS_OFFSET, GPS_UTC_DELTA = get_gps_utc_constants()

    for data_source_result_tuple in data_source_results:
        obsid = data_source_result_tuple[0]

        try:
            obsid_index = all_obsids.index(obsid)
        except Exception as e:
            continue

        utc_millis = (obsid - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000

        obsname = obsid_results[obsid_index][1]
        ra_phase_center = obsid_results[obsid_index][2]

        if obsname.startswith('low') and ra_phase_center == 0:
            for column_index in range(1, len(data_source_result_tuple)):
                column_name = columns[column_index - 1].name
                column_data = data_source_result_tuple[column_index]
                data['l0'][column_name].append([utc_millis, column_data])
            data['utc_obsid_map_l0'].append([utc_millis, obsid])
        elif obsname.startswith('low') and ra_phase_center == 60:
            for column_index in range(1, len(data_source_result_tuple)):
                column_name = columns[column_index - 1].name
                column_data = data_source_result_tuple[column_index]
                data['l1'][column_name].append([utc_millis, column_data])
            data['utc_obsid_map_l1'].append([utc_millis, obsid])
        elif obsname.startswith('high') and ra_phase_center == 0:
            for column_index in range(1, len(data_source_result_tuple)):
                column_name = columns[column_index - 1].name
                column_data = data_source_result_tuple[column_index]
                data['h0'][column_name].append([utc_millis, column_data])
            data['utc_obsid_map_h0'].append([utc_millis, obsid])
        elif obsname.startswith('high') and ra_phase_center == 60:
            for column_index in range(1, len(data_source_result_tuple)):
                column_name = columns[column_index - 1].name
                column_data = data_source_result_tuple[column_index]
                data['h1'][column_name].append([utc_millis, column_data])
            data['utc_obsid_map_h1'].append([utc_millis, obsid])

    return data

def get_lowhigh_and_eor_clauses(low_or_high, eor):
    low_high_clause = "" if low_or_high == 'any' else "AND obsname LIKE '" + low_or_high + "%'"

    eor_clause = ''

    if eor != 'any':
        if eor == 'EOR0':
            eor_clause = "AND ra_phase_center = 0"
        else:
            eor_clause = "AND ra_phase_center = 60"

    return (low_high_clause, eor_clause)

def join_with_obsids_from_set(data_source_results, the_set, data_source):
    low_high_clause, eor_clause = get_lowhigh_and_eor_clauses(the_set.low_or_high, the_set.eor)

    projectid_clause = "AND projectid='G0009'" if data_source.projectid else ""

    response = send_query(g.eor_db, '''SELECT starttime
                FROM mwa_setting
                WHERE starttime >= {} AND starttime <= {}
                {}
                {}
                {}
                ORDER BY starttime ASC'''.format(the_set.start, the_set.end,
                    projectid_clause, low_high_clause, eor_clause)).fetchall()

    obs_id_list = [obs_tuple[0] for obs_tuple in response]

    filtered_results = [obs_tuple for obs_tuple in data_source_results if obs_tuple[0] in obs_id_list]

    return filtered_results
