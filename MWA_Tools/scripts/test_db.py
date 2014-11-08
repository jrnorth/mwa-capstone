#! /usr/bin/env python
"""
test_db.py 
Tests importing of mwaconfig and connectivity to the database.
"""


import logging, sys, os, glob, string, re, urllib, math, time
from optparse import OptionParser
import numpy
#import pgdb
print "Setting up mwa environment"
import mwaconfig
print "using mwa.conf at: %s"%mwaconfig.CPfile
print 
print 
import ephem
print "importing mwa bits"
from mwapy import dbobj, ephem_utils
from mwapy.obssched.base import schedule
from mwapy.get_observation_info import *
try:
    from mwapy.pb import primarybeammap
    _useplotting=True
except ImportError:
    _useplotting=False    

dbuser = mwaconfig.mandc.dbuser
dbpassword = mwaconfig.mandc.dbpass
dbhost = mwaconfig.mandc.dbhost
dbname = mwaconfig.mandc.dbname


print "DB setup:"
print "dbuser =",dbuser
print "dbpassword = ", dbpassword
print "dbhost = ", dbhost
print "dbname = ",dbname
print 
print
# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('get_observation_info')
logger.setLevel(logging.WARNING)

print "testing connection to database"
# open up database connection
try:
    db = schedule.getdb()
except:
    logger.error("Unable to open connection to database")
    sys.exit(1)
print "Connected!"
