#!/flask/bin/python3.4

from app import models
from app.flask_app import db
from datetime import datetime, timedelta
from requests_futures.sessions import FuturesSession
import requests
import json

def update():
	# The Julian day for January 1, 2000 was 2,451,545 (http://en.wikipedia.org/wiki/Julian_day).
	jan_1_2000 = datetime(2000, 1, 1)

	jan_1_2000_julian_day = 2451545

	now = datetime.utcnow()

	eleven_minutes = timedelta(minutes = 11)

	# Start retrieving observation data from 11 minutes in the past. This script will be run every 10 minutes as a cron job;
	# the extra minute has been added as a buffer.
	past = now - eleven_minutes

	session = FuturesSession()

	baseUTCToGPSURL = 'http://ngas01.ivec.org/metadata/tconv/?utciso='

	requestURLStart = baseUTCToGPSURL + past.strftime("%Y-%m-%dT%H:%M:%S")

	requestURLEnd = baseUTCToGPSURL + now.strftime("%Y-%m-%dT%H:%M:%S")

	# Start the first Web service request in the background.
	future_start = session.get(requestURLStart)

	# The second request is started immediately.
	future_end = session.get(requestURLEnd)

	# Wait for the first request to complete, if it hasn't already.
	response_start = future_start.result()

	# Wait for the second request to complete, if it hasn't already.
	response_end = future_end.result()

	startGPS = response_start.content

	endGPS = response_end.content

	requestURL = 'http://ngas01.ivec.org/metadata/find'

	params = {'projectid': 'G0009', 'mintime': startGPS, 'maxtime': endGPS}

	# The list of observations in this 11-minute time period.
	data = json.loads(requests.get(requestURL, params=params).text)

	baseGPStoUTCURL = 'http://ngas01.ivec.org/metadata/tconv/?gpssec='

	for obs in data:
		# Get the observation's id.
		obs_id = obs[0]

		# Since the observation ID is a GPS time, we need to convert it back to UTC.
		requestURL = baseGPStoUTCURL + str(obs_id)

		obs_utc_str = json.loads(requests.get(requestURL).text)

		obs_utc = datetime.strptime(obs_utc_str, "%Y-%m-%dT%H:%M:%S")

		# Get the time delta between this observation date and January 1, 2000.
		delta = obs_utc - jan_1_2000

		# Add the number of days in the time delta to the Julian day to get this datetime's Julian day.
		julian_day = delta.days + jan_1_2000_julian_day

		datum = models.HistogramData(obs_id=obs_id, julian_day=julian_day)

		# Merge rather than add because the 1-minute buffer means we might insert existing entries into the table.
		db.session.merge(datum)

	print(str(len(data)) + ' new observations added to histogram')

	db.session.commit()

if __name__ == '__main__':
	update()
