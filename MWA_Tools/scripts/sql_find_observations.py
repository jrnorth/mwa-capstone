#!/usr/bin/python
"""
Finds MWA observations based on a project code and date range
DJacobs

Sept. 12 2012
"""
import mwaconfig

import optparse,logging,sys
from mwapy.obssched.base import schedule



o = optparse.OptionParser()
o.set_usage('find_observations.py [options] <obsids>')
o.set_description(__doc__)

o.add_option('--proj', type='str',
    help = 'Project ID')
o.add_option('-v',action='store_true',
    help='expand output into uncharted unparsable dimensions')
o.add_option('--list_projects', action='store_true',
    help = 'List available project ids and exit')
o.add_option('--dates',type='str',
    help="""Date range in UTC 'yyyy/mm/dd hr:mm:ss_yyyy/mm/dd hr:mm:ss', or just yyyy/mm/dd for the entire night (none
    of this option yet
    supported. No dates for you!)""")
o.add_option('--GPSrange',type='str',
    help="Date range in GPS time. START_STOP, Supercedes --dates option")
o.add_option('--withdata',action='store_true',
    help="Only include observations with data.")
o.add_option('--withcal',action='store_true',
    help="Only get data that are marked as calibrations")
o.add_option('--obsname',type='str',
    help='Match any part of an observation name')
o.add_option('--chan',type='int',default=None,
    help='Match to channel[12]')
opts, args = o.parse_args(sys.argv[1:])


logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('find_observations')
logger.setLevel(logging.CRITICAL)

# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)

if not opts.list_projects is None:
    cur = db.cursor()
    cur.execute('select * from mwa_project')
    records = cur.fetchall()
    if opts.v: print '\t'.join(['ID','Name','Description'])
    for rec in records:
        print '\t'.join([rec[0],rec[2]]),
        if opts.v:
            print '\t\t\t\t',rec[1]
        else:
            print
    sys.exit(0)
SQL_CONST = ''
if len(args)>0:
    SQL_CONST += ' where starttime IN ('+','.join(args)+') and '
else:
    SQL_CONST +=' where '
if not opts.GPSrange is None:
    try:
        GPSSTART,GPSSTOP = map(int,opts.GPSrange.split('_'))
        if GPSSTART>GPSSTOP: 
            print "Input Error: Stop is before Start"
            sys.exit(1)
    except:
        print "Syntax Error: %s"%opts.GPSrange
        sys.exit(1)
else:
    GPSSTART=0
    GPSSTOP=10**10
SQL_CONST += " starttime>%d and starttime<%d"%(GPSSTART,GPSSTOP)
if not opts.proj is None:
    SQL_CONST += " and projectid='%s'"%opts.proj
if not opts.obsname is None:
    SQL_CONST += " and obsname like '%%%s%%' "%opts.obsname
cur = db.cursor()
PSQL = "select starttime,obsname,creator,projectid,mode from mwa_setting" + SQL_CONST
PSQL+=' order by starttime'
sys.stdout.flush()
if opts.v:
    print PSQL
calfound=False
cur.execute(PSQL)
records = cur.fetchall()
if len(records)==0 and opts.v:
    print "no records found for GPS time range %s"%opts.GPSrange
for rec in records:
    if opts.chan is not None:
        cur.execute('select frequency_values from Obsc_Recv_Cmds where observation_number=%d' % rec[0])
        channels=cur.fetchall()[0][0]
        try:
            if channels[12] != opts.chan:
                # channel does not match specification
                continue
        except:
            pass

    if opts.withdata and not opts.v:
        cur.execute('select count(*) from data_files where observation_num=%d'%rec[0])
        filecount = cur.fetchall()[0][0]
        if filecount<1: continue
    elif opts.withdata and opts.v:
        cur.execute('select count(*) from data_files where observation_num=%d'%rec[0])
        filecount = cur.fetchall()[0][0]
    if opts.withcal:
        cur.execute('select calibration from schedule_metadata where observation_number=%d'%rec[0])
        iscal = cur.fetchall()[0][0]
        if iscal:
            print rec[0]
            calfound=True
    else:
        cur.execute('select calibration from schedule_metadata where observation_number=%d'%rec[0])
        print rec[0]
    if opts.v:
        print '\t'.join(rec[1:]),
        if opts.chan is not None:
            try:
                print '\t',channels[12],
            except:
                pass
        if opts.withdata: print '\t',filecount
        if opts.withcal: print "CAL"
        
if opts.withcal and not calfound: print "No calibrators found."
