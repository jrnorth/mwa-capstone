#! /usr/bin/env python

import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob,copy
import numpy,ephem
import itertools
from optparse import OptionParser,OptionGroup
from mwapy import ephem_utils, dbobj, get_observation_info, make_metafiles, eorpy
import psycopg2
import mwapy
import astropy.time,astropy.coordinates.angles
from astropy.table import Table,Column
import collections
from mwapy.eorpy import qcdb

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('scrape_qc')
logger.setLevel(logging.INFO)

Tables={'observation_info': {'key': 'obsid',
                             'object': qcdb.Observation_Info}}
try:
    import h5py
    formats=['hdf5','fits','vot','votable']
except:
    formats=['fits','vot','votable']    

usage="Usage: %prog [options]\n"
usage+="\tScrape the contents of the QC database, putting the results in a single HDF5 file\n"
parser = OptionParser(usage=usage,version=mwapy.__version__ + ' ' + mwapy.__date__)
parser.add_option('-o','--output',dest="output",default='qc.hdf5',
                  help="Output name for database contents [default=%default]")
parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                  help="Increase verbosity of output")
parser.add_option('-q','--quiet',action="store_false",dest="verbose",default=False,
                  help="Decrease verbosity of output")

(options, args) = parser.parse_args()

if (options.verbose):
    logger.setLevel(logging.INFO)

if os.path.exists(options.output):
    os.remove(options.output)

try:
    qcdbcon = qcdb.getdb()
    
except:
    logger.error("Unable to open connection to QC database")
    sys.exit(1)

n,f=os.path.splitext(options.output)
format=f.replace('.','')
if not format in formats:
    logger.error('Requested output format "%s" is not allowed\nPlease use %s' % (format,','.join(formats)))
    sys.exit(1)
    
x=qcdbcon.dsn.split()
dbname='%s@%s:%s:%s' % (x[1].split('=')[1],
                        x[3].split('=')[1],
                        x[0].split('=')[1],
                        x[4].split('=')[1])

logger.info('Connecting to QC database %s@%s:%s:%s'  % (x[1].split('=')[1],
                                                        x[3].split('=')[1],
                                                        x[0].split('=')[1],
                                                        x[4].split('=')[1]))

cur=qcdbcon.cursor()
for k in Tables.keys():
    record_list=collections.OrderedDict()

    try:
        cur.execute('select %s from %s' % (Tables[k]['key'],k))
        rows=cur.fetchall()
    except(psycopg2.InternalError, psycopg2.ProgrammingError) , e:
        logger.warning('Database error=%s' % (e.pgerror))
        qcdbcon.rollback()

    logger.info('Found %d rows in table <%s>' % (len(rows),k))
    for i in xrange(len(rows)):
        record_list[rows[i][0]]=Tables[k]['object'](rows[i][0],db=qcdbcon)

    columns=collections.OrderedDict()
    _file=eorpy._configdirectory + 'qc.' + k + '.def'
    try:
        column_data=Table.read(_file,format='ascii.commented_header',
                               delimiter='\s')
    except:
        logger.error('Unable to read table definition file %s' % (_file))
        sys.exit(1)
    t=Table(meta={'name': k,
                  'current': astropy.time.Time.now().iso})
    for i in xrange(len(column_data)):
        c=column_data[i]
        if '[' in c['type']:
            l=int(c['type'].split('[')[1].replace(']',''))
            d=c['type'].split('[')[0]
        else:
            d=c['type']
            l=1
        if d=='object':
            print 'Do not know how to handle this column:'
            print '\t%s' % c['column']
            continue
        if c['type'].startswith('S'):
            columns[c['column']]=Column(name=c['column'],
                                        dtype=d,
                                        length=len(rows))

        else:
            if c['unit'] != 'None':
                columns[c['column']]=Column(name=c['column'],
                                            dtype=d,
                                            unit=c['unit'],
                                            shape=(l,),
                                            length=len(rows))
            else:
                columns[c['column']]=Column(name=c['column'],
                                            dtype=d,
                                            shape=(l,),
                                            length=len(rows))

        t.add_column(columns[c['column']])
    for i in xrange(len(rows)):
        for j in xrange(len(column_data)):
            try:
                t[column_data[j]['column']][i]=record_list[rows[i][0]].__dict__[column_data[j]['column']]
            except:
                #print 'problem with row %d field %d(%s)' % (i,j,column_data[j]['column'])
                pass
    if format.lower()=='hdf5':
        if not os.path.exists(options.output):
            t.write(options.output, path=k, format='hdf5')        
        else:
            t.write(options.output, path=k, append=True, format='hdf5')
        print 'Table %s written to %s' % (k,options.output)
    elif format.lower() in ['fits','vot','votable']:
        if format.lower() in ['vot','votable']:
            writeformat='votable'
        if format.lower() in ['fits']:
            writeformat='fits'
        n,e=os.path.splitext(options.output)
        newoutput=n + '.' + k + e
        if os.path.exists(newoutput):
            os.remove(newoutput)
        t.write(newoutput,format=writeformat)
        print 'Table %s written to %s' % (k,newoutput)

    
qcdbcon.close()
