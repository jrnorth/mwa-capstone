import sys,os,logging,shutil,datetime,re,subprocess,math,tempfile,string,glob,copy
import numpy,ephem
import itertools
from optparse import OptionParser,OptionGroup
from mwapy import ephem_utils, dbobj, get_observation_info, make_metafiles
import psycopg2
import astropy.time,astropy.coordinates.angles
from astropy.table import Table,Column
from mwapy import eorpy

# and a second connection to the QC database
qcdbhost='eor-00.mit.edu'
qcdbname='mwa_qc'
qcdbuser='mwa'
qcdbpass='BowTie'
qcdbport=5432



######################################################################

def getdb(user=qcdbuser, password=qcdbpass,
          host=qcdbhost, database=qcdbname, port=qcdbport):
  """Returns a db object. This must be passed to all methods that interact
     with the database (__init__, save, getall, etc). A db object cannot
     be shared across threads, and after any changes to the database, 
     db.commit() must be called to make these changes visible to other
     db objects or connections. If db.rollback() is called instead, all
     changes are discarded.
  """

  dbob = dbobj.getdb(user=user, password=password, host=host, database=database, port=port)
  return dbob


######################################################################
def get_elevation_separation_azel(azimuth, elevation, GPStime, object='Sun'):
    mwa=ephem_utils.Obs[ephem_utils.obscode['MWA']]
    t=astropy.time.Time(GPStime,format='gps',scale='utc')
    observer=ephem.Observer()
    # make sure no refraction is included
    observer.pressure=0
    observer.long=mwa.long/ephem_utils.DEG_IN_RADIAN
    observer.lat=mwa.lat/ephem_utils.DEG_IN_RADIAN
    observer.elevation=mwa.elev
    observer.date=t.datetime.strftime('%Y/%m/%d %H:%M:%S')
    body=ephem.__dict__[object]()
    body.compute(observer)
    output_elevation=body.alt*ephem_utils.DEG_IN_RADIAN
    output_separation=ephem_utils.DEG_IN_RADIAN*ephem_utils.angulardistance(azimuth/15.0,elevation,
                                                                            body.az*ephem_utils.HRS_IN_RADIAN,
                                                                            body.alt*ephem_utils.DEG_IN_RADIAN)
    return output_separation, output_elevation


################################################################################
class Observation_Info(dbobj.dbObject):
  _table='observation_info'
  _file=eorpy._configdirectory + 'qc.' + _table + '.def'
  try:
      column_data=Table.read(_file,format='ascii.commented_header',delimiter='\s')
  except:
      print 'Could not find database definition file %s' % (_file)
  _attribs=[]
  for i in xrange(len(column_data)):
      c=column_data[i]
      if c['default']=='None':
          d=None
      elif c['default']=='False':
          d=False
      elif c['default']=='True':
          d=True
      else:
          try:
              d=int(c['default'])
          except:
              d=c['default']
      _attribs.append((c['column'],c['column'],d))
  _key = ('obsid',)  
  _readonly = ['modtime']
  _reprf = '%(obsid)s'
  _strf = 'Observation_Info[%(obsid)s]'
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname
