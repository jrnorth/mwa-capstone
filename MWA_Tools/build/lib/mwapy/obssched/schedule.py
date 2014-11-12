
"""
Look at:
http://mwa-lfd.haystack.mit.edu/twiki/bin/view/Main/DatabaseImplementation
for the table descriptions

Schedule interface module

This module defines classes that map onto the MWA schedule tables:   
  mwa_setting - the MWA_Setting class
  rf_stream - the RFstream class
  tile_selection_table - the Tileset class

An instance of any of classes can be created created by passing a db object
obtained using schedule.getdb() and a 'keyval' tuple. The keyval tuple 
contains the value/values in the relevant tables 'primary key'. For
MWA_Setting, the keyval is (starttime,), for RFstream the keyval is
(starttime,N) where N is the RFstream number for that starttime, and
for Tileset the keyval is (name,). 

If a record with the specified keyval exists in the database, the data
is loaded from the database and used to fill in the object attributes. If
the object contains sub-objects - for example, an MWA_Setting contains an 
arbitrary number of RFstream objects, and an RFstream object contains a 
Tileset - then these sub-objects are loaded from the database as well.

If a record with the specified keyval is NOT found in the database, then
an object is created anyway, but with empty (default) attributes, and the
attribute 'new' is True (if loaded from the database, new=False).

To create a new telescope setting for times Tstart-Tstop, the sequence is:

from base import schedule
db = schedule.getdb()
s = schedule.MWA_Setting(keyval=(Tstart,), db=db)
s.stoptime = Tstop
s.rfstreams.append( schedule.RFstream(keyval=(Tstart,0),db=db))
s.rfstreams[0].ra = 123.45
s.rfstreams[0].dec = -45.67
...
s.rfstreams[0].tileset = schedule.Tileset('all', db=db) 
s.save(db=db)

For a simple command line interface:

import schedule
db = schedule.getdb()
s = schedule.MWA_Setting(keyval=(Tstart,), db=db)
s.prompt(db=db)       #Answer all the prompts for configuration values
s.save(db=db)

"""

debug = False

__version__ = "$Rev$"

import mwaconfig

from mwapy import dbobj
try:
  from obssched.base import tiles
except ImportError:
  from mwapy.obssched.base import tiles

import time
import traceback
import os
import pwd
import cPickle
import logging
import re

try:
  dbuser = mwaconfig.mandc.dbuser
  dbpassword = mwaconfig.mandc.dbpass
  dbhost = mwaconfig.mandc.dbhost
  dbname = mwaconfig.mandc.dbname
  try:
    dbport = mwaconfig.mandc.dbport
  except AttributeError:
    dbport = 5432
except:
  dbuser,dbpassword,dhost,dbname,dbport = ('mwa','','mwa-db','mwa',5432)


def getdb(user=dbuser, password=dbpassword, host=dbhost, database=dbname, port=dbport):
  """Returns a db object. This must be passed to all methods that interact
     with the database (__init__, save, getall, etc). A db object cannot
     be shared across threads, and after any changes to the database, 
     db.commit() must be called to make these changes visible to other
     db objects or connections. If db.rollback() is called instead, all
     changes are discarded.
  """
  dbob = dbobj.getdb(user=user, password=password, host=host, database=database, port=port)
  return dbob


class SErr:
  """Error object to pass information on schedule parameter errors upstream from
     check() and save() methods in a machine-readable way.
  """
  def __init__(self,obj=None,parlist=[],mesg=''):
    """Create a schedule error object. Parameters are the object that the error
       occurred in (at the lowest level), a list of parameters at fault, and
       a human-readable error message.
    """
    self.obj = obj
    self.parlist = parlist
    self.mesg = mesg
    self.version = __version__
  def __repr__(self):
    return `self.obj`+`self.parlist`+':('+self.version+') -> '+self.mesg
  def __str__(self):
    return `self.obj`+`self.parlist`+':('+self.version+') -> '+self.mesg
  


class MWA_Setting(dbobj.dbObject):
  """This class defines a record in the mwa_setting table. A setting is a complete set
     of configuration information for the beamformers, receivers, correlator and RTS
     used to define the instantaneous behaviour of the telescope. A setting object has
     the following components:

     -starttime, stoptime: The times, in GPS seconds, over which this setting is
                to be applied. These times must both be integers, as changes
                to the configuration only happen on second boundaries. The starttime is used as the
                primary key in the database table, and also used to link this settings
                record with other tables, including the metadata archive.
                The obvious constraints apply - endtime>starttime, and
                endtime<=(any other starttime).
     -creator: Who entered this setting - person, daemon name, etc.
     -unpowered_tile_name: The name of the set of tiles to power down during this observation
     -modtime, a timestamp for when this record was last modified in the
                database. This attribute can be changed in the observation object, but the 
                value is not written back to the database - instead, the database server
                automatically sets this value when the record is altered.
     -mode, a text string defining the data reduction handler
     -ra_phase_center, dec_phase_center: RA and Dec of the commanded phase center,
                in decimal degrees; None if the commanded phase center was not specified in (RA,Dec).

     The above attributes are all stored in the mwa_setting table, and form part of the 
     database. There are also local attributes used to express the heirarchy of the linked
     tables:
 
     -rfstreams: This can contain a dict of rfstream objects (as many as desired) that form 
                part of this setting. The 'save' method of the setting object will call 'save'
                on any rfstream objects present in this list, committing them to the database.
                Note that rfstream objects can in turn contain tile selection objects, and they
                will be saved to the database when the rfstream objects are saved.
     -voltagebeams: This can contain a list of voltage beam objects (these are as yet undefined)
                defining correlator settings associated with this setting. If present, they are
                saved when save() is called on the setting object. 
     -rtsettings: This can contain an 'RTSsetting' object (this is as yet undefined) defining
                RTS configuration associated with this setting. If present, it is saved when
                save() is called on the setting object. 
     -logs:     This can contain a list of MWA_Log objects referring to the observation.
  """
  _table='mwa_setting'
  _attribs = [('starttime','starttime',0),
              ('stoptime','stoptime',0),
              ('obsname','obsname',''),
              ('creator','creator',''),
              ('unpowered_tile_name','unpowered_tile_name','default'),
              ('ra_phase_center','ra_phase_center',None),
              ('dec_phase_center','dec_phase_center',None),
              ('modtime','modtime',''),
              ('mode','mode',''),
              ('projectid','projectid','')]
  _readonly = ['modtime']
  _key = ('starttime',)
  _reprf = 'MWA_setting[%(starttime)s]'
  _strf = """[%(starttime)s - %(stoptime)s]:%(obsname)s={%(mode)s} - %(creator)s - %(projectid)s

  RA_phase/Dec_phase=%(ra_phase_center)s/%(dec_phase_center)s
  """
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname


  def __init__(self, keyval=(), db=None):
    """Initialise settings object and/or load from database.
    """
    self.rfstreams = {}
    self.voltagebeams = []
    self.rtssettings = None
    self.log = None   #Kept for legacy code, to be removed at some point.
    self.logs = []

    curs=db.cursor()
    dbobj.dbObject.__init__(self, keyval, db=db)   #Load from database or generate blank
    if not self.new:
      self.logs = getLogs(self.starttime, self.stoptime, db=db)
      allrfs = dbobj.execute('select starttime,number from rf_stream ' +
                             'where starttime=%s', (self.starttime,), db=db)
      db.commit()
      for r in allrfs:
        rfs = RFstream(keyval=r, db=db)
        self.rfstreams[rfs.number] = rfs


  def prompt(self, db=None):
    """Prompt the user to fill in data for a new setting.
    """
    print "\nDefining new MWA setting object:"
    if not self.starttime:
      self.starttime = int(raw_input('Enter start time (GPS seconds): '))
    self.stoptime = int(raw_input('Enter end time (GPS seconds): '))

    self.creator = raw_input('Enter Creator name: ').strip()
    self.mode = raw_input('Enter reduction mode: ').strip()

    self.unpowered_tile_name = raw_input('Enter name of unpowered tileset (default): ').strip()
    
    rfnum = int(raw_input('How many RF_Stream settings do you want? ').strip())
    for i in range(rfnum):
      rfs = RFstream(keyval=(self.starttime,i), db=db)
      rfs.prompt(db=db)
      self.rfstreams[rfs.number] = rfs
    self.logs.append(MWA_Log(keyval=None, db=db))
    self.logs[-1].prompt()

    #Ditto for voltage beams and RTS settings when they are defined


  def tilesetsOK(self):
    """Loop through all rfstreams and make sure that there is no overlap between
       tilesets in different rfstreams. Returns 'True' if there is no overlap, 
       'False' otherwise.
    """
    for r in self.rfstreams.values():
      for s in self.rfstreams.values():
        if r<>s and r.tileset.overlaps(s.tileset):
          return False
    return True


  def check(self, recursive=False, commit=True, db=None):
    """Make sure that this object, and all sub-objects contained (RFstreams, etc)
       pass consistency checks - no overlapping tiles, starttime/stoptimes, etc)
       Return a list of strings, each an error message. An empty list means no errors.
    """
    errors = []
    if self.stoptime <= self.starttime:
      errors.append(SErr(self,['starttime,stoptime'],"Stoptime must be greater than starttime."))
    conftimes = dbobj.execute('select starttime,stoptime from mwa_setting ' +
                             'where (starttime < %s) and '
                             '(stoptime > %s)', (self.stoptime,self.starttime),  db=db)
    for s in conftimes:
      if (s[0] == self.starttime) and (s[1] == self.stoptime):
        pass                    #Changing existing observation
      else:
        errors.append(SErr(self,['starttime,stoptime'],
                           "Overlaps in time with an already scheduled observation starting at %d." % (s[0],)))
    if not self.tilesetsOK():
      errors.append(SErr(self,['rfstreams'],
                         "Tilesets partially overlap, some tiles used by more than one RFstream."))
    if self.unpowered_tile_name:
      uptiles = dbobj.execute("select list from unpowered_tiles where name=%s", (self.unpowered_tile_name,), db=db)
      if len(uptiles) == 0:
        errors.append(SErr(self,['unpowered_tile_name'], "No entry %s in unpowered_tiles table" % self.unpowered_tile_name))
      if len(uptiles) > 1:
        errors.append(SErr(self,['unpowered_tile_name'], "Multiple entries %s in unpowered_tiles table" % self.unpowered_tile_name))
    if (not self.mode):
      self.mode=repr(Obs_Modes[getDefaultObsMode(db=db)])
    if recursive:
      for rfs in self.rfstreams.values():
        errors += rfs.check()
      for vb in self.voltagebeams:
        errors += vb.check()
      if self.rtssettings:
        errors += self.rtssettings.check()
      for log in self.logs:
        errors += log.check()
    if commit:
      db.commit()
    return errors
    

  def save(self, ask=False, force=True, commit=True, verbose=True, db=None):
    """Save settings object to database.
    """
    #autocommit_save = db.autocommit
    #if db.autocommit:
    #  db.autocommit = False
    try:
      errors = self.check(db=db, recursive=False, commit=False)
      if errors:
        if commit:
          db.commit()
        return errors
      dbobj.dbObject.save(self, ask=ask, force=force, db=db, commit=False, verbose=verbose)
      for rfs in self.rfstreams.values():
        errors += rfs.save(ask=ask, force=force, commit=False, verbose=verbose, db=db)
      for vb in self.voltagebeams:
        errors += vb.save(ask=ask, force=force, commit=False, verbose=verbose, db=db)
      if self.rtssettings:
        errors += self.rtssettings.save(ask=ask, force=force, commit=False, verbose=verbose, db=db)
      for log in self.logs:
        errors += log.save(ask=ask, force=force, commit=False, verbose=verbose, db=db)
      if commit:
        if errors:
          db.rollback()
          if verbose:
            print "Object '%s' not saved due to errors." % self
        else:
          db.commit()
          if verbose:
            print "Object '%s' saved." % self
    finally:
        pass
      #if autocommit_save:
      #  db.commit()
      #  db.autocommit = True
    return errors




class RFstream(dbobj.dbObject):
  """An object of this class describes a record in the 'rfstream' table. It consists of
     a 'tile_selection' record (the name of an entry in the tile_selection_table), and 
     collection of settings that apply to the tiles specified in that tile_selection.
     One telescope setting (an MWA_setting object) can have an arbitrary number of 
     rfstreams associated with it - in theory, every tile could have a different 
     configuration. Each rfstream record has the same starttime as the MWA_setting object
     that it is part of, and a 'number' (0 for the first rfstream of that MWA_setting, 
     1 for the second, 2 for the third, etc). 

     An rfstream object does not define a list of tiles explicitly, because in most cases,
     the precise tiles to be used won't be known when the schedule entry is created.
     Instead, the tile_selection will be something like "workingtiles", or 'EOR-default", 
     pre-defined records in the tile_selection table with tile lists that are kept up to
     date in real time using metadata on telescope performance. 

     The fields are:

     -starttime:  GPS seconds
     -number: an integer, starting from 0 for the first RF stream associated with a setting

     These two fields (starttime and number) form the primary key of the rf_stream table

     -azimuth, elevation: in degrees, None if the beamformer settings are not defined this way
     -ra,dec: in degrees, None if the beamformer settings are not defined this way
     -hex: Michael's hex beamformer delay specifier, '' if the beamformer settings are not defined this way

     The above fields define the beamformer delays for the specified tiles in one of three ways. 
     If more than one set of these fields are filled, the results are undefined.

     -tile_selection: The name of an entry in the tile_selection_table (text)
     -tileset: This can contain an object of the 'Tileset' class. The 'name' of
                tileset object should be the same as the 'tile_selection' field above, but it
                is the responsibility of the programmer to make sure that's true. The save 
                method of the rfstream object will call 'save' on the object in 'tileset',
                if it's defined (thus committing it to the database), but will pass if
                tileset is None. If tileset is defined, the name of that tileset object
                will be written to the tile_selection attribute of the rfstream object
                when it is saved.

     -dipole_exclusion: Text field which is the name of the entry in the dipole_exclusion_table
                to use for the tiles in this rf_stream object.

     -frequencies: A list (as in the python list type) of up to 24 integer channel numbers, 
            each between 90 and 255, in units of ~1.3 MHz
     -frequency_type: an entry from the Frequency_Types table
     -vsib_frequency: A value from the frequencies[] list
     -walsh_mode: 'ON' or 'OFF', or possibly other values in the future.
     -gain_control_type: A value from the Gain_Control_Types table
     -gain_control_value: Zero, one, or more value(s) in db, 
     -creator: Who entered this setting - person, daemon name, etc.
     -modtime, a timestamp for when this record was last modified in the
         database. This attribute can be changed in the observation object, but the 
         value is not written back to the database - instead, the database server
         automatically sets this value when the record is altered.

  """
  _table = 'rf_stream'
  _attribs = [('starttime','starttime',0),
              ('number','number',0),
              ('azimuth','azimuth',None),
              ('elevation','elevation',None),
              ('ra','ra',None),
              ('dec','dec',None),
              ('hex','hex',''),
              ('tile_selection','tile_selection',''),
              ('frequencies','frequencies',[]),
              ('frequency_type','frequency_type',''),
              ('vsib_frequency','vsib_frequency',None),
              ('walsh_mode','walsh_mode',''),
              ('gain_control_type','gain_control_type',''),
              ('gain_control_value','gain_control_value',None),
              ('dipole_exclusion','dipole_exclusion','default'),
              ('creator','creator',''),
              ('modtime','modtime','')]
  _readonly = ['modtime']
  _key = ('starttime','number')
  _reprf = 'RFstream[%(starttime)s:%(number)d]'
  _strf = """[%(starttime)s (%(number)d) - Az/El=%(azimuth)s/%(elevation)s
  RA/Dec=%(ra)s/%(dec)s
  hex=%(hex)s
  tile_selection=%(tile_selection)s
  dipole_exclusion=%(dipole_exclusion)s
  frequencies{%(frequency_type)s}=%(frequencies)s
  vsib_frequency=%(vsib_frequency)s
  walsh_mode=%(walsh_mode)s
  gain_control=%(gain_control_type)s: %(gain_control_value)s]
  """
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname


  def __init__(self, keyval=(), db=None):
    """Initialise rfstream object and/or load from database.
    """
    self.tileset = None
    dbobj.dbObject.__init__(self, keyval, db=db)   #Load from database or generate blank
    if not self.new:
      if self.tile_selection:
        self.tileset = Tileset(self.tile_selection, db=db)


  def prompt(self, db=None):
    """Prompt the user to fill in data for a new rfstream setting.
    """
    print "\nDefining new RF stream object: %d(%d)" % (self.starttime, self.number)
    ptype = int(raw_input("Enter coordinate type 1: Az/El, 2: RA/Dec or 3: Hex (1-3): "))
    if ptype == 1:
      self.azimuth = float(raw_input("Enter Azimuth in decimal degrees: "))
      self.elevation = float(raw_input("Enter Elevation in decimal degrees: "))
    if ptype == 2:
      self.ra = float(raw_input("Enter RA in decimal degrees: "))
      self.dec = float(raw_input("Enter Dec in decimal degrees: "))
    if ptype == 3:
      self.hex = raw_input("Enter Hex beamformer setting: ")

    gottiles = False
    while not gottiles:
      print """
  Enter tile selection - either a tile selection record name, or
  a full tile specifier. The tile specifier format is a series of
  space or comma separated specifiers, each of which has the
  form of a number or number span (eg "3" or "25-30"), followed
  by "x", "y", "xy", or no polarisation specifier (implying "xy").
  
  Examples include:
    eor_default
    all32
    1x, 2y, 3-8xy
    1-32x, 1-30y
    10 11 12 13x, 14y
  """
      tstring = raw_input("Enter tile selection: ").strip().lower()
      tsp = Tileset(tstring, db=db)    #See if the string given is a valid name in the database
      if not tsp.new:                  #If so, store the tileset object and name
        gottiles = True
        self.tile_selection = tstring
        self.tileset = tsp
      else:                            #Nothing of that name in database, so try it as a tilespec
        tsp = makeTileset(tilespec=tstring, db=db)
        if tsp:                        #If we get tileset object return, it's a valid tilespec
          gottiles = True
          self.tileset = tsp
          self.tile_selection = tsp.name   #use the autogenerated name
        else:
          print "Not a valid tile specifier, and no tile selection of that name\n"

    gotfreq = False
    while not gotfreq:
      print "Enter list of up to 24 frequency channels, each 90-255, comma seperated:"
      fls = raw_input("Channels: ").strip()
      try:
        fl = map(int,fls.split(','))
        if len(fl)>24:
          print "Too many channels - must be 24 or less\n"
        elif len(fl)<1:
          print "Must specify at least one channel\n"
        else:
          self.frequencies = fl
          gotfreq = True
      except ValueError:
        print "Error parsing channel list. Must be comma seperated list of integers.\n"
        

    wm = raw_input("Enter Walsh mode - 'on' or 'off': ").strip().upper()
    self.walsh_mode = wm   #Error checking?

    self.dipole_exclusion = raw_input("Enter name of dipole_exclusion_table entry to use: ")

    # DLK: this needs to be checked
    default_gaintype=MWA_Gain_Control_Types(keyval=(getDefaultGainType(db=db),),db=db)
    gt = raw_input("Gain control type (or leave blank for %s): " % repr(default_gaintype)).strip().upper()
    if (not gt):
      self.gain_control_type = repr(default_gaintype)
    else:
      self.gain_control_type=gt
    gaintype=MWA_Gain_Control_Types(keyval=(gt,),db=db)
    if (gaintype.takes_value):
        gv = raw_input("Gain control in db (or leave blank for default): ").strip().upper()        
        if not gv:
            gv=gaintype.default_value
        try:
            gv = float(gv)
            self.gain_control_value = gv
        except:
            print "Invalid gain control value '"+gv

    self.creator = raw_input("Enter creator name: ").strip()
    
 
  def check(self, recursive=False, commit=True, db=None):
    """Make sure that this object, and all sub-objects contained (Tileset, etc)
       pass consistency checks - no overlapping tiles, starttime/stoptimes, etc)
       Return a list of strings, each an error message. An empty list means no errors.
    """
    errors = []
    # which type of coordinate are we dealing with
    haveradec = (self.ra is not None and self.dec is not None)
    haveazel = (self.azimuth is not None and self.elevation is not None)
    havehex = (self.hex is not None) and (self.hex <> '')
    if (not haveradec and not haveazel and not havehex):
      errors.append(SErr(self,['ra','dec','azimuth','elevation','hex'],
                         'RFstream %d has no valid coordinate set.' % (self.number,)))
    if ( (haveradec and (haveazel or havehex)) or
         (haveazel and (haveradec or havehex)) or
         (havehex and (haveradec or haveazel)) ):
      errors.append(SErr(self,['ra','dec','azimuth','elevation','hex'],
                         'RFstream %d has more than one coordinate set.' % (self.number,)))
    if haveradec:
      if (self.ra<0.0) or (self.ra>360.0):
        errors.append(SErr(self,['ra'],'RFstream %d has invalid RA.' % (self.number,)))
      if (self.dec<-90.0) or (self.dec>90.0):
        errors.append(SErr(self,['dec'],'RFstream %d has invalid Dec.' % (self.number,)))
    if haveazel:
      if (self.azimuth<0.0) or (self.azimuth>360.0):
        errors.append(SErr(self,['azimuth'],
                           'RFstream %d has invalid Azimuth.' % (self.number,)))
      if (self.elevation<0.0) or (self.elevation>90.0):
        errors.append(SErr(self,['elevation'],
                           'RFstream %d has invalid Elevation.' % (self.number,)))
    if havehex:
      res = checkhex(hexcode = self.hex)
      if res:
        errors.append(SErr(self,'hex',res))

    if (self.frequency_type is None or self.frequency_type == ''):
      self.frequency_type=MWA_Frequency_Types(keyval=(getDefaultFrequencyType(db=db),),db=db)

    # DLK: updated for new Frequency_Types
    Frequency_Types=MWA_Frequency_Types.getdict(db=db)
    if not self.frequency_type in [repr(x) for x in Frequency_Types.itervalues()]:
      errors.append(SErr(self,['frequency_type'],
                         'RFstream %d has invalid frequency type: %s.' % (self.number,self.frequency_type)))
    frequency_key=MWA_Frequency_Types.getKey(self.frequency_type,db=db)

    # only if not BURST etc.
    if (Frequency_Types[frequency_key].takes_value):
      if type(self.frequencies) <> list:
        if type(self.frequencies) == set:
          self.frequencies = list(self.frequencies)     #Use of set is deprecated, but don't give an error for now.
        else:
          errors.append(SErr(self,['frequencies'],
                             'RFstream %d has frequency info in the wrong format.' % (self.number,)))
      if len(self.frequencies) > 24:
        errors.append(SErr(self,['frequencies'],
                           'RFstream %d has too many frequency channels.' % (self.number,)))
      if len(self.frequencies) == 0:
        errors.append(SErr(self,['frequencies'],
                           'RFstream %d has no frequency channels.' % (self.number,)))      
      for f in self.frequencies:
        if f<0 or f>255:
          errors.append(SErr(self,['frequencies'],
                             'RFstream %d has invalid channel: %d.' % (self.number,f)))    
      if (self.vsib_frequency is not None):
        if not self.vsib_frequency in self.frequencies:
          errors.append(SErr(self,['vsib_frequency'],
                             'RFstream %d has invalid vsib_frequency: %d.' % (self.number,self.vsib_frequency)))    
      else:
        # set it to the middle value by default
        if (self.frequencies is not None and len(self.frequencies)>0):
          self.vsib_frequency=self.frequencies[len(self.frequencies)/2]
    if (self.walsh_mode <> 'ON') and (self.walsh_mode <> 'OFF'):
      errors.append(SErr(self,['walsh_mode'],
                    'RFstream %d has invalid Walsh Mode: %s.' % (self.number,self.walsh_mode)))
    if self.dipole_exclusion:
      edipoles = dbobj.execute("select tile from dipole_exclusion_table where name=%s", (self.dipole_exclusion,), db=db)
      if len(edipoles) == 0:
        errors.append(SErr(self,['diple_exclusion'], "No entry %s in dipole_exclusion_table" % self.dipole_exclusion))
 
    # DLK: updated for new Gain_Control_Types
    Gain_Control_Types=MWA_Gain_Control_Types.getdict(db=db)
    if not self.gain_control_type in [repr(x) for x in Gain_Control_Types.itervalues()]:
        errors.append(SErr(self,['gain_control_type'],
                           'RFstream %d has invalid gain control type: %s.' % (self.number,self.gain_control_type)))
    gain_control_key=MWA_Gain_Control_Types.getKey(self.gain_control_type,db=db)
    if ( (self.gain_control_value is  None) and Gain_Control_Types[gain_control_key].takes_value):
        # get the default value
        self.gain_control_value=Gain_Control_Types[gain_control_key].default_value
    if (Gain_Control_Types[gain_control_key].takes_value):
        if ( (type(self.gain_control_value) <> float) and 
             (type(self.gain_control_value) <> int)  ):
            errors.append(SErr(self,['gain_control_value'],
                               'RFstream %d has invalid gain control value: %s.' % (self.number,`self.gain_control_value`)))

    if recursive:
      if self.tileset:
        errors += self.tileset.check(commit=False)
    if commit:
      db.commit()
    return errors


  def save(self, ask=False, force=True, commit=True, verbose=False, db=None):
    """Save rfstream object to database.
    """
    #autocommit_save = db.autocommit
    #if db.autocommit:
    #  db.autocommit = False
    try:
      errors = self.check(db=db, recursive=False, commit=False)
      if errors:
        if commit:
          db.commit()
        return errors
      if self.tileset:
        self.tile_selection = self.tileset.name
        if (self.tileset.new):
          errors += self.tileset.save(ask=ask, force=force, commit=False, verbose=verbose, db=db)
      dbobj.dbObject.save(self, ask=ask, force=force, commit=False, verbose=False, db=db)
      if commit:
        if errors:
          db.rollback()
          if verbose:
            print "Object '%s' not saved due to errors." % self
        else:
          db.commit()
          if verbose:
            print "Object '%s' saved." % self
    finally:
        pass
      #if autocommit_save:
      #  db.commit()
      #  db.autocommit = True
    return errors
   


class Tileset(dbobj.dbObject):
  _table='tile_selection_table'
  _attribs = [('name','name',''),
              ('xlist','xlist',set([])),
              ('ylist','ylist',set([])),
              ('creator','creator',''),
              ('modtime','modtime','')]
  _readonly = ['modtime']
  _key = ('name',)
  _reprf = 'Tile_Selection[%(name)s]'
  _strf = '%(name)s:\n  xlist=%(xlist)s\n  ylist=%(ylist)s'
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname


  def tr_d2o(self,name,value):
    if name=='xlist' or name=='ylist':
      return set(value)     #psycopg2 does type conversion to a Python list, but we want a set
    else:
      return value

  def tr_o2d(self,name,value):
    if name=='xlist' or name=='ylist':
      return list(value)    #Convert to a list before passing to psycopg2, it handles conversion to the right SQL query
    else:
      return value
      
  def check(self, db=None, recursive=False, commit=True):
    return []     #No tileset checking yet

  def specstring(self):
    return tiles.ftiles(self.xlist,self.ylist)

  def union(self,t2):
    "Performs a set union of this tileset with the argument"
    self.xlist = set(self.xlist) | set(t2.xlist)
    self.ylist = set(self.ylist) | set(t2.ylist)

  def intersection(self,t2):
    """returns only the tiles in both this tileset and the tileset given as an argument,
       with X and Y treated seperately.
    """
    self.xlist = set(self.xlist) & set(t2.xlist)
    self.ylist = set(self.ylist) & set(t2.ylist)

  def remove(self,t2):
    "remove all of the tiles in the argument from this tileset, treating X and Y seperately"
    self.xlist = set(self.xlist) - set(t2.xlist)
    self.ylist = set(self.ylist) - set(t2.ylist)

  def overlaps(self,t2):
    """returns true if there is any overlap in tiles between this tileset and the tileset
     given as an argument.
    """
    tx = set(self.xlist) & set(t2.xlist)
    ty = set(self.ylist) & set(t2.ylist)
    if tx or ty:
      return True
    else:
      return False
    
  def save(self, ask=False, force=True, commit=True, verbose=False, db=None):
    """Save tileset object to database.
    """
    errors = self.check(db=db, recursive=False, commit=False)
    if errors:
      if commit:
        db.commit()
      if verbose:
        print "Object '%s' not saved due to errors." % self
      return errors
    dbobj.dbObject.save(self, ask=ask, force=force, commit=commit, verbose=False, db=db)
    if verbose:
      print "Object '%s' saved." % self
    if commit:
      db.commit()
    return errors




def makeTileset(db=None, name=None, tilespec=''):
  """Return a tileset object given a tile_selection_table entry name, or a tile specifier, or both.

     If just a name is given, load the tileset of that name from tile_selection_table and return it.

     If just a tile specifier string is given, look at all the existing tileset entries in the table,
     and return an existing object that has a matching xlist and ylist, if there is one. If there
     isn't an object already defined with the same xlist and ylist, then create Tileset object and
     generate a unique name for it.

     If name AND tile specifier are both given, and there is an existing object in the database with 
     the name given, then the xlist and ylist of that object must match the tilespec given, or an 
     error is logged and 'None' is returned instead of a Tileset.

     If neither name nor tilespec are given, 'None' is returned and an error is logged.

     Note that if a new tilespec is created, not loaded from the database, then it is not saved,
     you must explicitly save it. This means that if you call this function twice with the same (new) 
     tilespec, it will return two different tilespec objects, both with the same (autogenerated) name
     and tile list. One will overwrite the other when saved, and they contain the same name and data,
     so it isn't likely to be an issue.
  """
  if tilespec:
    try:
      xl,yl = tiles.rtiles(tilespec)
    except tiles.TileSpecError:
      logging.error('Invalid tile specifier: '+tilespec)
      return

  if name:
    t = Tileset(name, db=db)
    if tilespec:
      if t.new:
        t.xlist, t.ylist = xl,yl
      else:
        if (t.xlist <> xl) or (t.ylist <> yl):
          logging.error('tile specifier given does not match entry in database by that name')
          return None
  else:
    if tilespec:
      t = None
      for te in Tileset.getall(db=db):
        if (te.xlist == xl)  and (te.ylist == yl):
          t = te
      if not t:
        name = 'tmp_' + tilespec.replace(' ','_')
        t = Tileset(name, db=db)
        t.xlist = xl
        t.ylist = yl
    else:
      logging.error('No tile specifier or name given')
      return None
  return t


######################################################################
# DLK: additional classes
 
######################################################################
class MWA_Log(dbobj.dbObject):
  _table = 'mwa_log'
  _attribs = [('comment','comment',''),
              ('referencetime','referencetime',0),
              ('logtype','logtype',1),
              ('creator','creator',''),
              ('modtime','modtime',''),
              ('endtime','endtime',None),
              ('log_id','log_id',None)]
  _readonly = ['modtime','log_id']
  _key = ('log_id',)
  _serialkey = True     #True if the primary key for this table is an autoincrementing sequence
  _reprf = 'MWA Log[%(log_id)s]'
  _strf = '%(log_id)d:(%(referencetime)d-%(endtime)d)[type=%(logtype)s]: %(comment)s'
  #_strf = '%s' % (self.referencetime)
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

  def __str__(self):
    """ override this method here to make it better"""
    return '%s:(%s-%s)[type=%s]: %s' % (self.log_id,self.referencetime,self.endtime,Log_Types[self.logtype],self.comment)

  def prompt(self):
      """prompt the user to fill in data for a new log entry
      """
      print "\nDefining new MWA Log object:"
      if (not self.referencetime):
        self.referencetime = int(raw_input('Enter reference time (GPS seconds): '))
      if (not self.endtime):
        self.endtime = int(raw_input('Enter end time that log entry refers to (0 for instantaneous) (GPS seconds): '))
        if self.endtime == 0:
          self.endtime = None
      print 'Available log types: %s' % Log_Types
      val = raw_input('Enter log type: ').strip()
      try:
        self.logtype = int(val)                
      except ValueError:
          # try to interpret the string
          for i in Log_Types.keys():
              if (val.lower() == repr(Log_Types[i]).lower()):
                  self.logtype = i
      self.comment = raw_input('Enter log comment: ').strip()

      self.creator = raw_input("Enter creator name: ").strip()     
      
  def check(self, db=None, recursive=False, commit=False):
    return []       #No checking of log messages yet.   


  def save(self, ask=False, force=True, commit=True, verbose=False, db=None):
    """Save Log object to database.
    """
    errors = self.check(db=db, recursive=False, commit=False)
    if errors:
      if commit:
        db.commit()
      if verbose:
        print "Object '%s' not saved due to errors." % self
      return errors
    dbobj.dbObject.save(self, ask=ask, force=force, commit=commit, verbose=0, db=db)
    if commit:
      db.commit()
    if verbose:
      print "Object '%s' saved." % self
    return errors


######################################################################
class MWA_Log_Types(dbobj.dbObject):
  _table = 'log_types'
  _attribs = [('number','type_num',0),
              ('type','log_type','')]
  _readonly = []
  _key = ('number',)
  _reprf = '%(type)s'
  _strf = 'Log Type[%(number)s]=%(type)s'
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

######################################################################
class MWA_Obs_Modes(dbobj.dbObject):
  _table = 'modes'
  _attribs = [('mode_id','mode_id',None),
              ('mode_name','mode_name',''),
              ('sync','sync',''),
              ('script','script',''),
              ('mode_parameters','mode_parameters',''),
              ('frequency_type','frequency_type',''),
              ('default_mode','default_mode',''),
              ('creator','creator',''),
              ('modtime','modtime','')]
  
  _readonly = []
  _key = ('mode_id',)
  _reprf = '%(mode_name)s'
  _strf = 'Observation Mode[%(mode_id)s]=%(mode_name)s, type=%(frequency_type)s'
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

  ##################################################
  # some utility functions
  # the table is indexed by number, but we will normally refer to the entries by name
  # these will help with that
  def getKey(cls, name=None, db=None):
      """
      return the index (key) associated with a given name
      """
      Obs_Modes=cls.getdict(db=db)
      key=None
      for i in Obs_Modes.iterkeys():
          if (repr(Obs_Modes[i])==name):
              key=i
      return key
  getKey = classmethod(getKey)

  def getObsMode(cls, name=None, db=None):
      """
      return the Obs_Mode entry associated with a given name
      """
      Obs_Modes=cls.getdict(db=db)
      key=None
      for i in Obs_Modes.iterkeys():
          if (repr(Obs_Modes[i])==name):
              key=i
      if not key is None:
          return Obs_Modes[key]
      else:
          return None
  getObsMode=classmethod(getObsMode)


######################################################################
class MWA_Gain_Control_Types(dbobj.dbObject):
  _table = 'gain_control_types'
  _attribs = [('type_id','type_id',None),
              ('type_name','type_name',''),
              ('default_type','default_type',''),
              ('takes_value','takes_value',True),
              ('default_value','default_value',None),
              ('sqlx','sqlx',''),
              ('sqly','sqly','')]
  
  _readonly = []
  _key = ('type_id',)
  _reprf = '%(type_name)s'
  _strf = 'Gain Control Mode[%(type_id)s]=%(type_name)s'
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname


  ##################################################
  # some utility functions
  # the table is indexed by number, but we will normally refer to the entries by name
  # these will help with that
  def getKey(cls, name=None, db=None):
      """
      return the index (key) associated with a given name
      """
      Gain_Control_Types=cls.getdict(db=db)
      key=None
      for i in Gain_Control_Types.iterkeys():
          if (repr(Gain_Control_Types[i])==name):
              key=i
      return key
  getKey = classmethod(getKey)

  def getGainControlType(cls, name=None, db=None):
      """
      return the Gain_Control_Type entry associated with a given name
      """
      Gain_Control_Types=cls.getdict(db=db)
      key=None
      for i in Gain_Control_Types.iterkeys():
          if (repr(Gain_Control_Types[i])==name):
              key=i
      if not key is None:
          return Gain_Control_Types[key]
      else:
          return None
  getGainControlType=classmethod(getGainControlType)

######################################################################
class MWA_Frequency_Types(dbobj.dbObject):
  _table = 'frequency_types'
  _attribs = [('type_id','type_id',None),
              ('type_name','type_name',''),
              ('default_type','default_type',''),
              ('takes_value','takes_value',True)
              ]
  
  _readonly = []
  _key = ('type_id',)
  _reprf = '%(type_name)s'
  _strf = 'Frequency Mode[%(type_id)s]=%(type_name)s'
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname


  ##################################################
  # some utility functions
  # the table is indexed by number, but we will normally refer to the entries by name
  # these will help with that
  def getKey(cls, name=None, db=None):
      """
      return the index (key) associated with a given name
      """
      Frequency_Types=cls.getdict(db=db)
      key=None
      for i in Frequency_Types.iterkeys():
          if (repr(Frequency_Types[i])==name):
              key=i
      return key
  getKey = classmethod(getKey)

  def getFrequencyType(cls, name=None, db=None):
      """
      return the Frequency_Type entry associated with a given name
      """
      Frequency_Types=cls.getdict(db=db)
      key=None
      for i in Frequency_Types.iterkeys():
          if (repr(Frequency_Types[i])==name):
              key=i
      if not key is None:
          return Frequency_Types[key]
      else:
          return None
  getFrequencyType=classmethod(getFrequencyType)


######################################################################
class MWA_Grid_Points(dbobj.dbObject):
  """
  A table to store gridded pointings where the delays match up well to sky positions
  The 'sigma' column is a floating point where lower values are better (in terms of a match)
  """
  _table = 'grid_points'
  _attribs = [('name','name',''),
              ('number','number',None),
              ('azimuth','azimuth',0),
              ('elevation','elevation',90),
              ('sigma','sigma',0),
              ('delays','delays',None)
              ]
  
  _readonly = []
  _key = ('name','number',)
  _reprf = '%(name)s(%(number)d)'
  _strf = 'Grid Pointing[%(name)s(%(number)d)]: Az=%(azimuth)07.3f deg, El=%(elevation)08.4f deg, sigma=%(sigma).3e'
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

######################################################################
class MWA_Skytemp(dbobj.dbObject):
  """
  A table to store predicted sky temperatures for a combination of grid points and LSTs
  LST is an integer formed from the LST in hours: int(LST*100+0.5) for faster indexing
  T1 and T2 are the prediced temperatures for the two polarizations
  dB1 and dB2 are predictions of the needed change in attenuation assuming Trecv=100 K and a nominal sky temperature is 175 K
  dB1 = 10*log10[ (Ta1+100)/275 ] dB
  values are computed for 150 MHz, and should be scaled to other frequencies by frequency^-2.6
  computed by Frank Briggs, 2013-04-25
  """
  _table = 'skytemp'
  _attribs = [('gridnum','gridnum',None),
              ('lst','lst',None),
              ('azimuth','azimuth',0),
              ('za','za',90),
              ('delays','delays',None),
              ('T1','T1',0),
              ('T2','T2',0),
              ('dB1','dB1',0),
              ('dB2','dB2',0),
              ]
  
  _readonly = []
  _key = ('gridnum','lst',)
  _reprf = '%(gridnum)s(%(lst)d)'
  _strf = 'Tsky[150 MHz,grid=%(gridnum)d,LST=%(lst)d/100 h]: Az=%(azimuth)07.3f deg, ZA=%(za)08.4f deg, T1=%(T1).1f K, T2=%(T2).1f K, dB1=%(dB1).1f, dB2=%(dB2).1f'
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

######################################################################
class MWA_Data_Files(dbobj.dbObject):
  """
  A table to store the data_files written
  both correlated data and associated meta-data
  
  """
  _table = 'data_files'
  _attribs = [('observation_num','observation_num',0),
              ('filetype','filetype',0),
              ('size','size',0),
              ('filename','filename',''),
              ('site_path','site_path',''),
              ('mit_path','mit_path',''),
              ('host','host',''),
              ('mit_host','mit_host',''),
              ('modtime','modtime','')              
              ]
  
  _readonly = ['modtime']
  _key = ('filename','observation_num',)
  _reprf = 'MWA_File[%(filename)s-%(observation_num)s]'
  _strf = """%(observation_num)s: %(size)s bytes, type=%(filetype)s\n\t%(host)s:%(site_path)s/%(filename)s (site)\n\t%(mit_host)s:%(mit_path)s/%(filename)s (MIT)"""
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

######################################################################
class Obsc_Recv_Cmds(dbobj.dbObject):
  """
  Table for ObsController to record the commands sent to the receivers

  """
  _table = 'obsc_recv_cmds'
  _attribs = [('rx_id','rx_id',None),
              ('starttime','starttime',0),
              ('stoptime','stoptime',0),
              ('observation_number','observation_number',0),
              ('observing_status','observing_status',''),
              ('slot_power','slot_power',[]),
              ('xdelaysetting','xdelaysetting',[]),
              ('ydelaysetting','ydelaysetting',[]),
              ('frequency_type','frequency_type',''),
              ('frequency_values','frequency_values',[]),
              ('walsh_state','walsh_state',''),
              ('x_gain_control_type','x_gain_control_type',[]),
              ('x_gain_control_values','x_gain_control_values',[]),
              ('y_gain_control_type','y_gain_control_type',[]),
              ('y_gain_control_values','y_gain_control_values',[]),
              ('vsib_frequency','vsib_frequency',0)
              ]
  
  _readonly = []
  _key = ('rx_id','starttime',)
  _reprf = '%(rx_id)s-%(starttime)s'
  _strf = ''
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname


######################################################################
class MWA_Project(dbobj.dbObject):
  """
  Project ID table with allowed keys.
  Referenced in mwa_setting, used in datafile names and used by the NGAS system for internal rounding.

  
  """
  _table = 'mwa_project'
  _attribs = [('projectid','projectid',''),
              ('description','description',''),
              ('shortname','shortname',''),
              ]
  
  _readonly = ['modtime']
  _key = ('projectid',)
  _reprf = '%(shortname)s'
  _strf = """%(projectid)s: (%(shortname)s)\n\t%(description)s"""
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

######################################################################
class Schedule_Metadata(dbobj.dbObject):
  """
  Holds essential meta-data for easier sorting
  
  """
  _table = 'schedule_metadata'
  _attribs = [('observation_number','observation_number',0),
              ('azimuth_pointing','azimuth_pointing',None),
              ('elevation_pointing','elevation_pointing',None),
              ('ra_pointing','ra_pointing',None),
              ('dec_pointing','dec_pointing',None),
              ('sun_elevation','sun_elevation',None),
              ('sun_pointing_distance','sun_pointing_distance',None),
              ('jupiter_pointing_distance','jupiter_pointing_distance',None),
              ('moon_pointing_distance','moon_pointing_distance',None),
              ('sky_temp','sky_temp',None),
              ('calibration','calibration',False),
              ('calibrators','calibrators',''),
              ('gridpoint_name','gridpoint_name',''),
              ('gridpoint_number','gridpoint_number',None),
              ('local_sidereal_time_deg','local_sidereal_time_deg',None)
              ]
  
  _readonly = []
  _key = ('observation_number',)
  _reprf = 'Schedule_Metadata[%(observation_number)s]'
  _strf = """%(observation_number)d:
  \t(Az,El)=(%(azimuth_pointing)s/%(elevation_pointing)s)
  \t(RA/Dec)=%(ra_pointing)s/%(dec_pointing)s
  \tLST=%(local_sidereal_time_deg)s deg
  \tSun at %(sun_elevation)s deg above horizon
  \tSource at %(sun_pointing_distance)s deg from Sun, %(jupiter_pointing_distance)s deg from Jupiter, %(moon_pointing_distance)s deg from Moon
  \tSky=%(sky_temp)s K"""

  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

  def __str__(self):
    s="%d:\n" % self.observation_number
    if self.azimuth_pointing is not None:
      s+='\t(Az,El)=(%.5f,%.5f) deg\n' % (self.azimuth_pointing,self.elevation_pointing)
    if self.ra_pointing is not None:
      s+='\t(RA,Dec)=(%.5f,%.5f) deg\n' % (self.ra_pointing, self.dec_pointing)
    if self.local_sidereal_time_deg is not None:
      s+='\tLST=%.5f deg\n' % (self.local_sidereal_time_deg)
    if self.sun_elevation is not None:
      s+='\tSun at %.1f deg above horizon\n' % (self.sun_elevation)
    if self.sun_pointing_distance is not None:
      s+='\tSource at %.1f deg from Sun, %.1f deg from Jupiter, %.1f deg from Moon\n' % (self.sun_pointing_distance,
                                                                                         self.jupiter_pointing_distance,
                                                                                         self.moon_pointing_distance)
    if self.sky_temp is not None:
      s+='\tSky temperature: %.1f K\n' % self.sky_temp
    if (self.calibration):
      s+='\tCalibration observation: %s\n' % self.calibrators
    if (len(self.gridpoint_name)>0):
      s+='\tGrid: %s(%d)\n' % (self.gridpoint_name, self.gridpoint_number)

    return s
######################################################################
class MWA_Tile(dbobj.dbObject):
  """
  basic information (position, connection) about MWA Tiles

  
  """
  _table = 'tile_info'
  _attribs = [('tile_id','tile_id',''),
              ('begintime','begintime',''),
              ('endtime','endtime',''),
              ('tile_pos_east','tile_pos_east',None),
              ('tile_pos_north','tile_pos_north',None),
              ('tile_altitude','tile_altitude',None),
              ('beamformer_id','beamformer_id',None),
              ('modtime','modtime',''),
              ('id','id',None)
              ]
  
  _readonly = ['modtime','id']
  _key = ('id',)
  _reprf = '%(tile_id)s,%(begintime)s'
  _strf = """%(tile_id)s: %(begintime)s-%(endtime)s %(tile_pos_east)s E %(tile_pos_north)s N %(tile_altitude)s m"""
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

######################################################################
# Other Functions
######################################################################

def checkhex(hexcode, nwords=16, separator=","):
    """  Written by David Kaplan
    checks whether the hexcode is valid
    the hexcode should be <nwords> * 6-bit words, separated by <separator>
    """
    maxvalue=int('111111',2)
    hexcodes=re.split(separator + '\s*',hexcode)
    hexcodedecvals=[int(y,16) for y in hexcodes]
    if ((len(hexcodes) != nwords) or (max(hexcodedecvals)>maxvalue) or (min(hexcodedecvals)<0)):
      return 'Beamformer delay Hexcode is not valid'


def verifyfields(db=None):
  """Check that database fields match _attrib definitions for all tables
     defined in classes, and print warning messages for any mismatch.
  """
  MWA_Setting.verifyfields(db=db)
  RFstream.verifyfields(db=db)
  Tileset.verifyfields(db=db)

  MWA_Log.verifyfields(db=db)
  MWA_Log_Types.verifyfields(db=db)
  MWA_Obs_Modes.verifyfields(db=db)
  MWA_Gain_Control_Types.verifyfields(db=db)
  MWA_Frequency_Types.verifyfields(db=db)


def getSettings(db=None, pagesize=20, page=None, mintime=None, maxtime=None):
  """Return a list of MWA_Setting objects in database. If maxtime or
     mintime is given, return a filtered list of settings, otherwise return all
     of them. If pagesize is non-zero, return 'pagesize' entries at a time. If
     pagesize is nonzero and 'page' is an integer less than or equal to the number
     of pages in total, return that page. If 'page' is a value in GPS seconds, 
     return the page that contains that starttime. If page is not valid or not 
     specified, return the last page. Page numbers count from one, not zero.

     The returned data is a tuple: (output, pageinfo), where 'output' is a list
     of MWA_Setting objects, and 'pageinfo' is a tuple: (page, pages), where 'page' 
     is the pagenumber returned and 'pages' is the total number of pages in the
     database.

     Be very wary of asking for too many results - returning any more than a few
     hundred results takes a very long time, tens of seconds on the Mac Mini. If
     in doubt about the number of results in a given time range, specify a page 
     size and use multiple queries if necessary.
  """
  if mintime is None:
    mintime = 0
  if maxtime is None:
    maxtime = 2147483647
  res = dbobj.execute('select starttime from mwa_setting where starttime >= %s and starttime < %s order by starttime', (int(mintime),int(maxtime)), db=db ) 
  db.commit()
  total = len(res)
  output = []
  if not pagesize:
    for stt in res:
      output.append(MWA_Setting(stt, db=db))
      page,pages = (1,1)
  else:
    p,m = divmod(total,pagesize)
    if m:
      pages = p + 1
    else:
      pages = p
    if (not page) or (page<1) or (type(page)<>int and
                                  type(page)<>long and
                                  type(page)<>float):
      page = pages
    if page > 10000000:    #A GPSseconds value
      for i in range(len(res)-1,-1,-1):
        if res[i][0] < page:
          p,m = divmod(i,pagesize)
          if m:
            page = p + 1
          else:
            page = p
          break
    elif page > pages:
      page = pages
    st,fi = (page-1)*pagesize, page*pagesize
    for stt in res[st:fi]:
      output.append(MWA_Setting(stt, db=db))
  return output,(page,pages)


def getStartstoptimes(db=None, mintime=None, maxtime=None, key='stoptime', sort=False):
    """
    starttimes,stoptimes=getStartstoptimes(db=None, mintime=None, maxtime=None, key='stoptime',sort=False)
    returns a list of starttimes and stoptimes for entries in the MWA_Setting table
    these have <key> between <mintime> and <maxtime>, where <key> can be starttime or stoptime
    """
    if mintime is None:
        mintime = 0
    if maxtime is None:
        maxtime = 2147483647
    if (key != 'stoptime' and key != 'starttime'):
        logging.error('Can only return results based on key=starttime or stoptime')
        return None
    sortcommand=''
    if (sort):
        sortcommand='order by starttime'
    query = 'select (starttime,stoptime) from '+MWA_Setting._table+' where '+key+' >= %s and '+key+' < %s '+ sortcommand
    db.commit()
    results=dbobj.execute(query, (int(mintime),int(maxtime)), db=db )        
    starttimes=[]
    stoptimes=[]
    for res in results:
        starttime,stoptime=res[0].split(',')
        starttime=long(starttime.replace('(',''))
        stoptime=long(stoptime.replace(')',''))
        starttimes.append((starttime))
        stoptimes.append((stoptime))        
    return starttimes,stoptimes


    
def getLogs(starttime=0, stoptime=2147483647, db=None):
  logids = dbobj.execute('select log_id from mwa_log ' +
                           'where ( (referencetime < %(stoptime)s) and '
                           '(endtime > %(starttime)s) ) ' +
                           'or ( (referencetime >= %(starttime)s) and '
                           '(referencetime < %(stoptime)s) and '
                           '(endtime is NULL) )', 
                           {'starttime':starttime, 'stoptime':stoptime}, db=db)
  db.commit()
  logs = []
  for s in logids:
    logs.append(MWA_Log(keyval=s[0], db=db))
  return logs

#######################################################################
def getdata_andpickle(databasecommand, picklename, timedifference=86400, db=None):
  """
  Data=getdata_andpickle(databasecommand, picklename, timedifference=86400, db=None)
  will retrieve a given database table and store a local copy.  on subsequent calls, will look first
  for local copy (if it is less than timedifference seconds old)
  example:

  Log_Types=getdata_andpickle(MWA_Log_Types.getdict, 'Log_Types', db=getdb())

  stored file is /tmp/Log_Types.<username>.cache
  """
  cachefile='/tmp/' + picklename +  '.' + pwd.getpwuid(os.getuid())[0] + '.cache'
  try:
    ltf = open(cachefile,'r')
    lmt, Output = cPickle.load(ltf)
  except:
    lmt,Output=0,{}
  if (time.time()-lmt) > timedifference:
    # get database dictionaries
    # open up database connection    
    try:
      Output=databasecommand(db=db)
      if os.path.exists(cachefile+'.tmp'):
        os.remove(cachefile+'.tmp')
      ltf = open(cachefile+'.tmp','w')
      cPickle.dump( (time.time(),Output), ltf)
      ltf.close()
      if os.path.exists(cachefile):
        os.remove(cachefile)
      os.rename(cachefile+'.tmp',cachefile)
    except OSError:
      logging.warn("%s cache can't be updated, file owned by another user.",picklename)
    except:
      logging.error("Unable to update " + picklename + " cache file\n" + 
                    traceback.format_exc())
  return Output

################################################################################
# load in local copies of the necessary tables for quicker access

tempdb=getdb()  
Log_Types=getdata_andpickle(MWA_Log_Types.getdict, 'Log_Types', db=tempdb)
Obs_Modes=getdata_andpickle(MWA_Obs_Modes.getdict, 'Obs_Modes', db=tempdb)
Gain_Control_Types=getdata_andpickle(MWA_Gain_Control_Types.getdict, 'Gain_Control_Types', db=tempdb)
Frequency_Types=getdata_andpickle(MWA_Frequency_Types.getdict, 'Frequency_Types', db=tempdb)
Grid_Points=getdata_andpickle(MWA_Grid_Points.getall, 'Grid_Points', db=tempdb)
Tile_List=getdata_andpickle(Tileset.getall, 'Tile_List', db=tempdb)
Projects=getdata_andpickle(MWA_Project.getdict, 'Projects', db=tempdb)

################################################################################
def getDefaultGainType(db=None):
      """ returns the index of the default gain_control_type
      """
      try:
        types=Gain_Control_Types
      except:
        types=MWA_Gain_Control_Types.getdict(db=db)
      for type in types.keys():
          if (types[type].default_type):
              return type
      return None

################################################################################
def getDefaultObsMode(db=None):
      """ returns the index of the default Obs Mode
      """
      try:
        modes=Obs_Modes
      except:
        modes=MWA_Obs_Modes.getdict(db=db)
      for mode in modes.keys():
        if (modes[mode].default_mode):
          return mode
      return None

################################################################################
def getDefaultFrequencyType(db=None):
      """ returns the index of the default FrequencyType
      """
      try:
        types=Frequency_Types
      except:
        types=MWA_Frequency_Types.getdict(db=db)
      for type in types.keys():
        if (types[type].default_type):
          return type
      return None

#print 'connecting to database'
#defdb = getdb()
#print 'connected'
#verifyfields(db=defdb)


