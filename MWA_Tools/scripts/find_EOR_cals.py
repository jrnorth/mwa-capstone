#! /usr/bin/env python
import sys,os

date = str(sys.argv[1])

y,m,d = date.split('-')


times = os.popen('timeconvert.py --year=%s --month=%s --day=%s' % (y,m,d)).read()
gps_start = (times.split('\n')[3]).split()[1]
mjd_start = (times.split('\n')[4]).split()[1]

next_mjd = str(float(mjd_start) + 1)

times = os.popen('timeconvert.py --mjd=%s' % (next_mjd)).read()
gps_end = (times.split('\n')[3]).split()[1]

cmd = 'find_observations.py --proj=G0009 --GPSrange=%s_%s --withcal' % (gps_start,gps_end)

obs = (os.popen(cmd).read())[:-1] #Remove trailing newline

print obs

