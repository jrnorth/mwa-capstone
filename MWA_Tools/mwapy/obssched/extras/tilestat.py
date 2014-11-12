
import psycopg2

import Image, ImageDraw
import random
from visual import *

#-------- database code ------------
db = psycopg2.connect(host='csr-dyn-24.mit.edu',user='mwa',password='BowTie')
curs = db.cursor()
curs.execute('select tile_id,tile_pos_east,tile_pos_north from tile_position')
c = curs.fetchall()

#--------- 2D graphic code ----------

img = Image.new('RGB', (800,800), (255,255,255) )
draw = ImageDraw.Draw(img)
for tile in c:
  id,east,north = tile
  if random.random()>0.1:
    tcol = (0,255,0)
  else:
    tcol = (255,0,0)
  xp = east*2 + 400 - 4
  yp = north*2 + 400 - 4
  draw.rectangle( (xp,yp,xp+8,yp+8), fill=tcol, outline=(0,0,0) )
  draw.text( (xp+8, yp+8), `id`, fill=(0,0,0) )
img.save('mwa.gif')
  
#----------- 3D graphic creation --------------
scene = display(title='MWA status', x=0, y=0, uniform=1, width=1500, height=1000)
ground = box( pos=(0.0,0.0,-0.1), size=(360.0,360.0,0.1), color=color.blue)
tiles = {}
for tile in c:
  id,east,north = tile
  tiles[id] = box( pos=(east,north,0.5), size=(4.0,4.0,1.0), color=color.white)

#------------ 3D graphic animation -------------
time.sleep(1)
while true:
  for t in tiles.keys():
    if random.random()>0.1:
      tiles[t].color = color.green
    else:
      tiles[t].color = color.red
  rate(1)
  
