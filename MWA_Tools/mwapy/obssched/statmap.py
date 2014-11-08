#!/usr/bin/python

import Image,ImageDraw
import os

import mwaconfig

from obssched import tilestatus
from mwapy.dbobj import execute

NumTiles = int(mwaconfig.glob.numtiles)

imgfile = '/tmp/mwa.png'

imscale = 2    #Pixels per metre
imecentre = 0.0
imncentre = 0.0
imsize = (800,800)

ImageBackground = (255,255,255)
TileLabel = (0,0,0)
TileOutline = (0,0,0)
IdleColor = (64,64,64)
ActiveColor = (0,255,0)
ErrorColor = (255,0,0)

def bname(fname):
  return os.path.basename(fname)

def m2xy(pos=(0,0)):
  """Takes a position on the ground in metres East and metres North and returns
     The X,Y pixel coordinates in the image map.
  """
  return imsize[0]/2 + (pos[0]-imecentre)*imscale, imsize[1]-(imsize[1]/2 + (pos[1]-imncentre)*imscale)


def drawDipole(Dr=None, did=1, pol=None, tx=0 ,ty=0 ,tr=0):
  """Given a Draw object Dr, a dipole id 'did', a tile's centre coord in pixels tx,ty, the
     tile's 'radius' (half the side length) in pixels, and the polarisation (X or Y), draw
     a red horizontal or vertical bar to indicate a disabled dipole.
  """
  dpr = tr/4
  dy,dx = divmod(did-1,4)
#  dy = 3-dy   #North is at higher Y values
  dy,dx = ty + dy*dpr*2 - dpr*3, tx + dx*dpr*2 - dpr*3
  fillcolor = None
  if pol == 'X':
    rec = (dx-dpr, dy-dpr/3, dx+dpr, dy+dpr/3)
    fillcolor = ErrorColor
  elif pol == 'Y':
    rec = (dx-dpr/3, dy-dpr, dx+dpr/3, dy+dpr)
    fillcolor = ErrorColor
  else:
    rec = (dx-dpr, dy-dpr, dx+dpr, dy+dpr)
  Dr.rectangle(rec, fill=fillcolor, outline=TileOutline)
  return dx,dy,dpr


def getdb():
  return tilestatus.getdb()


def getnow(db=None):
  n = execute('select gpsnow()', db=db)[0][0]
  db.commit()
  return n


def MakeImage(db=None, ctile=None, tilerad=None, stile=None, etile=None, dpx=True ):
  global imscale, imsize, imecentre, imncentre

  tiles = tilestatus.getTileStatus(db=db)
  now = getnow(db=db)
  if ctile and tilerad:
    if tilerad == 1:
      stile = ctile
      etile = ctile
    else:
      stile = divmod(ctile-tilerad, NumTiles)[1]
      etile = divmod(ctile+tilerad, NumTiles)[1]
  if not stile or stile<1:
    stile = 1
  if not etile or etile > NumTiles:
    etile = NumTiles
  if etile >= stile:
    tlist = range(stile,etile+1)
  else:
    tlist = range(stile,NumTiles+1) + range(1,etile+1)

  minn,maxn,mine,maxe = 10e3,-10e3,10e3,-10e3
  for t in tlist:
    trec = tiles[t]
    if mine > trec.pos[0]:
      mine = trec.pos[0]
    if maxe < trec.pos[0]:
      maxe = trec.pos[0]
    if minn > trec.pos[1]:
      minn =trec.pos[1] 
    if maxn < trec.pos[1]:
      maxn = trec.pos[1] 
    
  erange = maxe - mine
  nrange = maxn - minn
  escale = int(imsize[0]/(erange+20.0))
  nscale = int(imsize[1]/(nrange+10))
  imscale = min(escale,nscale)
  imecentre = (maxe+mine)/2.0
  imncentre = (maxn+minn)/2.0

  rsbsize = imsize[0]/8
  bestsb = 999999
  bestmatch = 9999999
  for sb in [1,2,5,10,20,50,100,200,500,1000,2000,5000]:
    if bestmatch > abs(rsbsize - sb*imscale):
      bestsb = sb
      bestmatch = abs(rsbsize - sb*imscale)

  sbsize = bestsb*imscale  #in pixels
  sbval = bestsb           #in metres
    
  Im = Image.new('RGB',imsize, ImageBackground)
  Dr = ImageDraw.Draw(Im)
  Dr.line( (30,30,30+sbsize,30), fill=TileOutline)
  Dr.line( (30,25,30,35), fill=TileOutline)
  Dr.line( (30+sbsize,25,30+sbsize,35), fill=TileOutline)
  Dr.text( (40,45), "%d metres" % (sbval,), fill=TileLabel)
  tilecoords = []
  dipolecoords = []
  for tid in tlist:
    t = tiles[tid]
    tx,ty = m2xy(t.pos)
    tr = 2.5*imscale
    Dr.rectangle( (tx-tr, ty-tr, tx+tr, ty+tr), fill=IdleColor, outline=TileOutline)
    if t.yinschedule:
      if t.recstatus == 'Observing':
        Dr.rectangle( (tx-tr, ty-tr/3, tx+tr, ty+tr/3), fill=ActiveColor, outline=ActiveColor)
      else:
        Dr.rectangle( (tx-tr, ty-tr/3, tx+tr, ty+tr/3), fill=ErrorColor, outline=ErrorColor)
    if t.xinschedule:
      if t.recstatus == 'Observing':
        Dr.rectangle( (tx-tr/3, ty-tr, tx+tr/3, ty+tr), fill=ActiveColor, outline=ActiveColor)
      else:
        Dr.rectangle( (tx-tr/3, ty-tr, tx+tr/3, ty+tr), fill=ErrorColor, outline=ErrorColor)
    tlabel = '%d: BF:%d RX:%d' % (tid,t.bf,t.receiver)
    altlabel = "Tile %d" % (tid,)
    titlelabel = "Tile %d, BF#:%s, Rec#:%s, BFTemp:%s, AttenX,Y:%s,%s db" % (tid,
                            t.bf, t.receiver, t.BFtemp, t.AttenX, t.AttenY)
    Dr.text( (tx+tr, ty+tr), tlabel, fill=TileLabel)
    tilecoords.append( (tid,'shape="rect" coords="%d,%d,%d,%d"' % (tx-tr,ty-tr,tx+tr,ty+tr) +
                            ' alt="%s" title="%s"' % (altlabel,titlelabel)) )
    if dpx:   #Draw excluded dipoles
      dipolecoords = []
      for did in range(1,16):
        dx,dy,dpr = drawDipole(Dr, did, None, tx,ty,tr)   #Draw outline of dipole box
        altlabel = "Dipole %d / %s" % (did, ([' ']+map(chr,range(65,65+16)))[did])
        titlelabel = altlabel
        dipolecoords.append( (did,
                              'shape="rect" coords="%d,%d,%d,%d"' % (dx-dpr,dy-dpr,dx+dpr,dy+dpr) +
                              'alt="%s" title="%s"' % (altlabel,titlelabel) ) )
      if t.ds.exclude_x_dipoles or t.ds.exclude_y_dipoles:   #If dipoles on this tile are excluded
        for xpol in t.ds.exclude_x_dipoles:
          drawDipole(Dr, xpol, 'X', tx,ty,tr)
        for ypol in t.ds.exclude_y_dipoles:
          drawDipole(Dr, ypol, 'Y', tx,ty,tr)
          
  if stile==etile:
    return Im, dipolecoords, tiles
  else:
    return Im, tilecoords, tiles
  

if __name__ == "__main__":
  db = getdb()
  img,coords,tiles = MakeImage(db=db)
  img.save(imgfile)


