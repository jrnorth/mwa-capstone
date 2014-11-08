#!/usr/bin/python

import cPickle
import logging
import socket

import mwaconfig

try:
  from obssched.base import schedule
  from obssched import dipole
except ImportError:
  from mwapy.obssched.base import schedule
  from mwapy.obssched import dipole
from mwapy.dbobj import execute

NumTiles = int(mwaconfig.glob.numtiles)

try:
  STATPORT = int(mwaconfig.mandc.statusport)      #The port that serves status message requests
except AttributeError:
  STATPORT = 9999


getdb = schedule.getdb


def getRxStatus():
  # Get the current system status
  sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
      sock.connect(('',STATPORT))
  except socket.error:
      logging.info("Couldn't connect to status monitor")
      return
  data=''
  while True:
    r = sock.recv(8192)
    if not r:
      break
    data+=r
  sock.close()
  return cPickle.loads(data)



class Tile(dict):
  """Inherit from the dict class, but override set_attr and get_attr so we can use either value['name']
     or value.name to refer to the items in the dictionary.

     Can be converted directly to a dict using dict(value) for pickling/JSON/etc.
  """
  def __setattr__(self,n,v):
   self[n] = v

  def __getattr__(self,n):
   if n in self:
     return self[n]
   else:
     return dict.__getattr__(n)


class Receiver(dict):
  """Inherit from the dict class, but override set_attr and get_attr so we can use either value['name']
     or value.name to refer to the items in the dictionary.

     Can be converted directly to a dict using dict(value) for pickling/JSON/etc.
  """
  def __setattr__(self,n,v):
   self[n] = v

  def __getattr__(self,n):
   if n in self:
     return self[n]
   else:
     return dict.__getattr__(n)


def getTiles(reftime=None, db=None):
  if db is None:
    db = getdb()

  tiles = {}

  if type(reftime) != int:
    reftime = int(execute('select gpsnow()', db=db)[0][0])

  tileinfo = execute('select ti.tile_id, ti.tile_pos_east, ti.tile_pos_north, ti.tile_altitude, ti.beamformer_id, ' +
                        'tc.receiver_id, tc.receiver_slot, pc.correlator_index,  cpm.corr_product_index, '
                        'bi.gain_x, bi.gain_y, cf.flavor, cf.attenuation_offset, bool(tf.tile_id) as flag, ' +
                        'ci.eleclength - ri.fibre_length/cv2.velocity_factor as tile_electrical_delay, ' +
                        'digital_gain_multipliers ' +
                     'from tile_info ti ' +
                          'left outer join tile_flags tf on (tf.tile_id = ti.tile_id and '
                                                             'tf.starttime < %(reftime)s and '
                                                             'tf.stoptime > %(reftime)s) ' +
                          'inner join beamformer_info bi on (ti.beamformer_id = bi.beamformer_id and '
                                                            'bi.begintime < %(reftime)s and bi.endtime > %(reftime)s) ' +
                          'inner join tile_connection tc on (ti.tile_id = tc.tile and ' +
                                                            'tc.begintime < %(reftime)s and tc.endtime > %(reftime)s) ' +
                          'inner join receiver_info ri on (ri.receiver_id = tc.receiver_id and ' +
                                                          'ri.begintime < %(reftime)s and ri.endtime > %(reftime)s) ' +
                          'inner join cable_info ci on (tc.cable_name = ci.name and ' +
                                                       "ci.begintime < %(reftime)s and ci.endtime > %(reftime)s) " +
                          "inner join cable_velocity_factor cv2 on cv2.type = 'fiber' " +
                          'inner join cable_flavor cf on (cf.flavor = ci.flavor and ' +
                                                         'cf.begintime < %(reftime)s and cf.endtime > %(reftime)s) ' +
                          'inner join pfb_receiver_connection pr on (pr.rx_id = tc.receiver_id and ' +
                                                                    'pr.begintime < %(reftime)s and pr.endtime > %(reftime)s) ' +
                          'inner join pfb_correlator_mapping pc on (pc.pfb_id = pr.pfb_id and pc.pfb_slot = pr.pfb_slot and ' +
                                                                   'pc.begintime < %(reftime)s and pc.endtime > %(reftime)s) ' +
                          'inner join siteconfig_tilecorrproductmapping cpm on cpm.rx_slot = tc.receiver_slot ' +
                     'where ' +
                           'ti.begintime < %(reftime)s and ti.endtime > %(reftime)s',
                     data={'reftime':reftime}, db=db)

  for tinf in tileinfo:
    tid, teast, tnorth, talt, tbfid, rid, rslot, corrindex, corprodindex, tbfgainx, tbfgainy, cflavor, tcatten, flagged, ted, dgains = tinf
    inputnum = (corrindex - 1) * 8 + corprodindex + 1   # Miriad correlator input numbers start at 1, not 0
    tiles[tid] = Tile(id=tid, pos=(teast,tnorth), altitude=talt, bf=tbfid, receiver=rid, slot=rslot,
                      inputnum=inputnum, bfgainx=tbfgainx, bfgainy=tbfgainy, flavor=cflavor, catten=tcatten,
                      flagged=flagged, ted=ted, dgains=dgains)
  return tiles


def getConnectionInfo(reftime=None, db=None):
  if db is None:
    db = getdb()

  receivers = {}
  corrinputs = {}

  if type(reftime) != int:
    reftime = int(execute('select gpsnow()', db=db)[0][0])

  tiles = getTiles(reftime=reftime, db=db)

  for tid,tile in tiles.items():
    corrinputs[tile.inputnum] = tile
    if tile.receiver not in receivers:
      sbc_name = 'rec%02d' % tile.receiver
      receivers[tile.receiver] = Receiver(id=tile.receiver, sbc_name=sbc_name)
      receivers[tile.receiver]['slots'] = {}   # Can't pass an empty dict to the constructor, or all receivers would share the same one
    receivers[tile.receiver].slots[tile.slot] = tile

  return receivers, tiles, corrinputs


def getobsid(filename=None, db=None):
  """Given a filename, return the obs_id associated with that filename.
  """
  if db is None:
    db = getdb()

  # If we are given a filename instead of an obsid, find the right obsid for that filename
  if filename is not None:
    curs = db.cursor()
    curs.execute('select observation_num from data_files where filename=%s', (filename,))
    res = curs.fetchall()
    if res:
      return int(res[0][0])
    else:
      return None


def getlastobs(db=None):
  """Return the obs_id of the most recent executed observation.
  """
  if db is None:
    db = getdb()

  curs = db.cursor()
  curs.execute('select starttime from mwa_setting where starttime <= (select gpsnow()) order by starttime desc limit 1')
  res = curs.fetchall()
  if res:
    return int(res[0][0])
  else:
    return None



def getObservationInfo(obsid=None, filename=None, db=None):
  if db is None:
    db = getdb()

  # If we weren't given an obsid, find one:
  if obsid is None:
    if filename is not None:
      obsid = getobsid(filename=filename, db=db)    # If we were given a filename, find the obsid for that filename
    else:
      obsid = getlastobs(db=db)    # If there's no filename parameter, use the most recent observation.

  if not obsid:
    return None

  # Grab an MWA_Setting object, and loop over the RF_Streams inside it
  ob = schedule.MWA_Setting(obsid, db=db)
  curs = db.cursor()
  obscrecmds = {}      # Cached contents of obsc_recv_cmds data, with recid as a key and tuples as values
  for rfnum,rfs in ob.rfstreams.items():   # For each RF_Stream:

    # Define rfs.bad_dipoles for the dipole_exclusion entries in this rfstream - a dict with tileid as a key.
    curs.execute("""select tile, exclude_x_dipoles, exclude_y_dipoles from dipole_exclusion_table where name=%(name)s and
                           begintime < %(obsid)s and endtime > %(obsid)s""", {'name':rfs.dipole_exclusion,
                                                                               'obsid':int(ob.starttime)})
    res = curs.fetchall()
    bad_dipoles = {}
    for row in res:
      tileid, xlist, ylist = row
      bad_dipoles[tileid] = (xlist, ylist)
    rfs.bad_dipoles = bad_dipoles

    # Find a single set of 'good' (no excluded dipoles, etc) delay values for the pointing in this rfstream.
    # At the same time, cache all the obsc_recv_cmds data for each receiver as we go, for later use.
    delays = None
    tmpdelays = None
    for tileid in rfs.tileset.xlist:   # Loop over all X-polarisation tiles in this RFStream
      if tileid not in bad_dipoles:
        recid = int(tileid / 10)
        if recid not in obscrecmds:
          curs.execute('select observing_status, slot_power, xdelaysetting, ydelaysetting from obsc_recv_cmds where ' +
                       'rx_id=%s and starttime=%s', (recid, int(ob.starttime)))
          res = curs.fetchall()
          if res:
            obscrecmds[recid] = res[0]
          else:
            obscrecmds[recid] = None
        if obscrecmds[recid] and obscrecmds[recid][2] and (0 <= (tileid - 10*recid - 1) <= 7):  # Too slow to do a proper connectivity lookup here,
          tmpdelays = obscrecmds[recid][2][tileid - 10*recid - 1]                               # so this hack rules out crashing on tile 79 (AAVS)
        if (delays is None) and (tmpdelays is not None) and (None not in tmpdelays):
          delays = tmpdelays
    if delays is None or len(obscrecmds.keys()) < 16:   # If we haven't found a valid pointing yet, or we haven't cached all 16 receiver commands records, try the Y-list
      for tileid in rfs.tileset.ylist:   # Loop over all Y-polarisation tiles in this RFStream
        if tileid not in bad_dipoles:
          recid = int(tileid / 10)
          if recid not in obscrecmds:
            curs.execute('select observing_status, slot_power, xdelaysetting, ydelaysetting from obsc_recv_cmds where ' +
                         'rx_id=%s and starttime=%s', (recid, int(ob.starttime)))
            res = curs.fetchall()
          if res:
            obscrecmds[recid] = res[0]
          else:
            obscrecmds[recid] = None
        if obscrecmds[recid] and obscrecmds[recid][3] and (0 <= (tileid - 10*recid - 1) <= 7):  # Too slow to do a proper connectivity lookup here,
          tmpdelays = obscrecmds[recid][3][tileid - 10*recid - 1]                               # so this hack rules out crashing on tile 79 (AAVS)
        if (delays is None) and (tmpdelays is not None) and (None not in tmpdelays):
          delays = tmpdelays
    rfs.delays = delays    # Set the master 'delays' attribute for the pointing for this rf_stream entry.

    # Now define rfs.bad_tiles containing any tiles in this rfstream with hardware (receiver or tile) faults.
    # At this point, we've cached an obsc_recv_cmds row in obscrecmds[recid] for every receiver with a tile in this rfstream
    bad_tiles = []   # List of tile numbers where slot_power is false, or the receiver status indicates a fault (eg, not connected)
    rfs.bad_tiles = []
    for recid, data in obscrecmds.items():
      if data:
        status, slot_powers, xdelays, ydelays = data
        if status.strip() != 'Observing':            # If there's a receiver fault, flag all tiles on it as bad
          bad_tiles = range(recid*10+1, recid*10+9)
        for slot in range(1,9):
          if (not slot_powers) or (not slot_powers[slot-1]):  # Flag any tiles with a slot_powers entry of False.
            bad_tiles.append(recid*10 + slot)
        for tile in bad_tiles:
          if ((tile in rfs.tileset.xlist or tile in rfs.tileset.ylist)) and (tile not in rfs.bad_tiles):
            rfs.bad_tiles.append(tile)    # Set the list of bad tiles for this rfstream, avoiding duplicates.
    rfs.bad_tiles.sort()

  # Now collect a list of all data files associated with this observation, and put it into ob.files
  ob.files = {}
  curs.execute("""select filename, filetype, size, host, site_path
                  from data_files
                  where observation_num=%s""", (int(ob.starttime),))
  res = curs.fetchall()
  if res:
    for row in res:
      filename, filetype, size, host, site_path = row
      ob.files[filename] = dict(filetype=filetype,
                                size=size,
                                host=host,
                                site_path=site_path)
  else:
    ob.files[filename] = dict(filetype=None,
                              size=None,
                              host=None,
                              site_path=None)

  # Now collect all the schedule_metadata info for this observation, and put it into ob.metadata
  curs.execute("""select azimuth_pointing, elevation_pointing, ra_pointing, dec_pointing,
                         sun_elevation, sun_pointing_distance, jupiter_pointing_distance, moon_pointing_distance,
                         sky_temp, calibration, calibrators,
                         gridpoint_name, gridpoint_number, local_sidereal_time_deg
                  from schedule_metadata where observation_number=%s""", (int(ob.starttime),))
  res = curs.fetchall()
  if res:
    azp, elp, rap, decp, sunel, sunpd, juppd, moonpd, skytemp, calib, calibrators, gridname, gridnum, lst_deg = res[0]
    ob.metadata = dict(azimuth_pointing=azp, elevation_pointing=elp, ra_pointing=rap, dec_pointing=decp,
                       sun_elevation=sunel, sun_pointing_distance=sunpd, jupiter_pointing_distance=juppd,
                       moon_pointing_distance=moonpd, sky_temp=skytemp, calibration=calib, calibrators=calibrators,
                       gridpoint_name=gridname, gridpoint_number=gridnum, local_sidereal_time_deg=lst_deg)
  else:
    ob.metadata = dict(azimuth_pointing=None, elevation_pointing=None, ra_pointing=None, dec_pointing=None,
                 sun_elevation=None, sun_pointing_distance=None, jupiter_pointing_distance=None,
                 moon_pointing_distance=None, sky_temp=None, calibration=None, calibrators=[],
                 gridpoint_name=None, gridpoint_number=None, local_sidereal_time_deg=None)


  # Now convert the MWA_Setting object and entire heirarchy, uncluding RF_Stream objects, into dictionaries, for
  # transport using JSON.
  obd = {}
  for attrib in ob.__dict__:
    if attrib == 'modtime':
      pass
    elif attrib == 'logs':
      obd['logs'] = [str(logent) for logent in ob.logs]
    elif attrib == 'rfstreams':
      obd['rfstreams'] = {}
      for rfid,rfs in ob.rfstreams.items():
        rfd = {}
        for rfattrib in rfs.__dict__:
          if rfattrib == 'modtime':
            pass
          elif rfattrib == 'tileset':
            t = rfs.tileset
            rfd['tileset'] = dict(name=t.name, creator=t.creator, xlist=list(t.xlist), ylist=list(t.ylist))
          else:
            rfd[rfattrib] = rfs.__dict__[rfattrib]
        obd['rfstreams'][rfid] = rfd
    else:
      obd[attrib] = ob.__dict__[attrib]

  return obd

  

if __name__ == "__main__":
  db = getdb()
#  img = MakeImage(db=db)
#  img.save(imgfile)


