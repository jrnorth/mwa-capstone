from app import db_utils, models
from flask import g

def get_error_counts(start_gps, end_gps):
    error_counts = []
    error_count = 0

    obscontroller_response = db_utils.send_query(g.eor_db, '''SELECT FLOOR(reference_time) AS reference_time
                            FROM obscontroller_log
                            WHERE reference_time >= {} AND reference_time <= {}
                            ORDER BY reference_time ASC'''.format(start_gps, end_gps)).fetchall()

    recvstatuspolice_response = db_utils.send_query(g.eor_db, '''SELECT FLOOR(reference_time) AS reference_time
                            FROM recvstatuspolice_log
                            WHERE reference_time >= {} AND reference_time <= {}
                            ORDER BY reference_time ASC'''.format(start_gps, end_gps)).fetchall()

    GPS_LEAP_SECONDS_OFFSET, GPS_UTC_DELTA = db_utils.get_gps_utc_constants()

    prev_time = 0

    for error in obscontroller_response:
        utc_millis = int((error[0] - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000)
        if utc_millis == prev_time:
            error_counts[-1][1] += 1
        else:
            error_counts.append([utc_millis, 1])
            prev_time = utc_millis
        error_count += 1

    prev_time = 0

    for error in recvstatuspolice_response:
        utc_millis = int((error[0] - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000)
        if utc_millis == prev_time:
            error_counts[-1][1] += 1
        else:
            error_counts.append([utc_millis, 1])
            prev_time = utc_millis
        error_count += 1

    error_counts.sort(key=lambda error: error[0])

    return (error_counts, error_count)

def get_observation_counts(start_gps, end_gps, low_or_high, eor):
    low_high_clause = "" if low_or_high == 'any' else "AND obsname LIKE '" + low_or_high + "%'"

    eor_clause = ''

    if eor != 'any':
        if eor == 'EOR0':
            eor_clause = "AND ra_phase_center = 0"
        else:
            eor_clause = "AND ra_phase_center = 60"

    response = db_utils.send_query(g.eor_db, '''SELECT starttime
                FROM mwa_setting
                WHERE starttime >= {} AND starttime <= {}
                AND projectid='G0009'
                {}
                {}
                ORDER BY starttime ASC'''.format(start_gps, end_gps, low_high_clause, eor_clause)).fetchall()

    GPS_LEAP_SECONDS_OFFSET, GPS_UTC_DELTA = db_utils.get_gps_utc_constants()

    observation_counts = []

    for observation in response:
        utc_millis = int((observation[0] - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000)
        observation_counts.append([utc_millis, 1])

    return observation_counts

def get_plot_bands(the_set):
    flagged_subsets = models.FlaggedSubset.query.filter(models.FlaggedSubset.set_id == the_set.id).all()

    GPS_LEAP_SECONDS_OFFSET, GPS_UTC_DELTA = db_utils.get_gps_utc_constants()

    plot_bands = [{'from': int((flagged_subset.start - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000),
        'to': int((flagged_subset.end - GPS_LEAP_SECONDS_OFFSET + GPS_UTC_DELTA) * 1000),
        'color': 'yellow'}
        for flagged_subset in flagged_subsets]

    return plot_bands
