#!/usr/bin/python

import cPickle
import logging
import socket

import mwaconfig

from obssched.base import schedule
from obssched import dipole
from mwapy.dbobj import execute

NumTiles = int(mwaconfig.glob.numtiles)

STATPORT=31001

def getdb():
  return schedule.getdb()


def getnow(db=None):
  n = execute('select gpsnow()', db=db)[0][0]
  db.commit()
  return n


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



class Tile():
  def __init__(self, id=0, pos=(0.0,0.0), altitude=0.0, bf=0, receiver=None, slot=None):
    self.id = id
    self.pos = pos
    self.altitude = altitude
    self.bf = bf
    self.receiver = receiver
    self.slot = slot
    self.xinschedule, self.yinschedule = False, False
    self.AttenX, self.AttenY = None,None
    self.BFtemp = None
    ds = None

class Receiver():
  def __init__(self, id=0, sbc_name=''):
    self.id = id
    self.sbc_name = sbc_name
    self.slots={}
  

def getConnectionInfo(db=None):
  tiles = {}
  receivers = {}
  now = getnow(db=db)

  recinfo = execute('select receiver_id,sbc_name from receiver_info where begintime <= %s and endtime > %s ', (now,now), db=db)
  for rec in recinfo:
    recid,sbc_name = rec[0],rec[1]
    receivers[recid] = Receiver(id=recid, sbc_name=sbc_name)
  
  tileinfo = execute('select tile_id,tile_pos_east,tile_pos_north,tile_altitude,beamformer_id ' +
                        'from tile_info where begintime <= %s and endtime > %s ', (now,now), 
                        db=db)

  minn,maxn,mine,maxe = 10e3,-10e3,10e3,-10e3
  for tinf in tileinfo:
    tiles[tinf[0]] = Tile(id=tinf[0], pos=(tinf[1],tinf[2]), altitude=tinf[3], bf=tinf[4])
    
  coninfo = execute('select tile,receiver_id,receiver_slot ' +
                    'from tile_connection where begintime <= %s and endtime > %s', (now,now),
                    db=db)
  db.commit()
  for cinf in coninfo:
    if cinf[0] not in tiles.keys():
      print "Error - tile_connection record for tile that isn't in tileinfo"
    else:
      tiles[cinf[0]].receiver = cinf[1]
      tiles[cinf[0]].slot = cinf[2]

  for tid in tiles.keys():
    t = tiles[tid]
    ds = dipole.DipoleState(keyval=tid, db=db)
    tiles[tid].ds = ds
    if (t.receiver is not None) and (t.slot is not None) and t.receiver in receivers.keys():
      receivers[t.receiver].slots[t.slot] = t
    
  return receivers,tiles



def getTileStatus(db=None):
  receivers,tiles = getConnectionInfo(db=db)
  idle = False
  sched = None
  now = getnow(db=db)

  schedinfo = execute('select starttime from mwa_setting where %s >= starttime and %s <= stoptime', (now,now), db=db)
  db.commit()
  status = getRxStatus()

  if len(schedinfo) == 0:
    idle = True
  elif len(schedinfo) == 1:
    sched = schedule.MWA_Setting(schedinfo[0][0], db=db)
    idle = False
  if sched:
    for tid,trec in tiles.items():
      for r in sched.rfstreams.values():
        if tid in r.tileset.xlist:
          trec.xinschedule = True
        if tid in r.tileset.ylist:
          trec.yinschedule = True

  for tid,trec in tiles.items():
    if trec.receiver and trec.slot and trec.receiver in status:
      st = status[trec.receiver]
      try:
        trec.BFtemp = float(st.BFs[trec.slot].Temp)
      except:
        trec.BFtemp = None
      try:
        xAttenUps = map(int,st.ASCs[1].AttenUp.split(' '))
        xAttenLos = map(int,st.ASCs[1].AttenLo.split(' '))
        yAttenUps = map(int,st.ASCs[2].AttenUp.split(' '))
        yAttenLos = map(int,st.ASCs[2].AttenLo.split(' '))
        trec.AttenX = xAttenUps[trec.slot-1] + xAttenLos[trec.slot-1]
        trec.AttenY = yAttenUps[trec.slot-1] + yAttenLos[trec.slot-1]
      except:
        trec.AttenX, trec.AttenY = None,None
      trec.recstatus = st.DigRxStatus
  return tiles

          

  

if __name__ == "__main__":
  db = getdb()
#  img = MakeImage(db=db)
#  img.save(imgfile)


