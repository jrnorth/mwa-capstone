#!/usr/bin/python
# a small script to convert the output of the instrument condig query in make_metafiles.sh
# to the standard corr2uvfits format for antenna_locations and instrument_config files
# Randall Wayth. April 2013.

import sys

antfilename="antenna_locations.txt"
instrfilename="instr_config.txt"

class Corr2UVFITS_Tile:
  def __init__(self,line):
    """"Constructor requiring a line from the all-in-one DB query for MWA config"""
    cols=line.strip().split('|')   
    self.rx_id = cols[0].strip()
    self.rx_active = True
    if cols[1].strip() == 'f': self.rx_active = False
    self.name = cols[2].strip()
    self.slot_powers = cols[3].strip()
    self.corr_ind = cols[4].strip()
    self.corr_prod_ind = cols[5].strip()
    self.elec_length = cols[6].strip()
    self.pos_east = cols[7].strip()
    self.pos_north = cols[8].strip()
    self.pos_up = cols[9].strip()
    self.flag = cols[10].strip()
    self.status = cols[11].strip()

  def __repr__(self):
    return "< "+self.name+" >"

def usage():
  print >> sys.stderr, "Usage: "+sys.argv[0]+" filename"
  print >> sys.stderr, "\tuse '-' for filename to read from stdin"
  sys.exit(0);

def makeInstConfig(alltiles):
  res = ''
  ant_ind=0
  corr_ind=0
  res += "# instrument config file for corr2uvfits\n"
  res += "# lines beginning with '#' and blank lines are ignored. Do not leave spaces in empty lines.\n"
  res += "# INDEX\tANTENNA\tPOL\tDELTA\t\tFLAG\n"
  for tile in alltiles:
    flagchar="0"
    if tile.flag != '' or tile.rx_active==False or tile.slot_powers=='' or tile.status=='Fault': flagchar="1"
    for pol in ['Y','X']:
        res += str(corr_ind) + "\t" + str(ant_ind) + "\t" + pol +"\t"+ "EL_"+tile.elec_length + "\t" + flagchar + "\t# " + tile.name + "\n"
        corr_ind +=1
    ant_ind += 1
  return res

def makeAntLocations(alltiles):
  res = ''
  ant_ind=1
  res += '# corr2uvfits antenna locations\n'
  res += "# lines beginning with '#' and blank lines are ignored. Do not leave spaces in empty lines.\n"
  res += '# locations of antennas relative to the centre of the array in local topocentric\n'
  res += '# "east", "north", "height". Units are meters.\n'
  res += '# Format: Antenna_name east north height\n'
  res += '# antenna names must be 8 chars or less\n'
  res += '# fields are separated by white space\n'
  for tile in alltiles:
    res += tile.name + "\t" +tile.pos_east+ "    \t" + tile.pos_north+ "    \t" + tile.pos_up + "    \t# Miriad index: "+str(ant_ind) + "\n"
    ant_ind += 1
  return res

def loadFile(infp):
  alltiles=[]
  for line in infp:
    if line[0]=='#' or line[0]=='\n':
      continue
    alltiles.append(Corr2UVFITS_Tile(line));
  return alltiles
 

if __name__ == "__main__":

  infp=sys.stdin

  if len(sys.argv)==1:
    usage();
  if sys.argv[1]=='-':
    fp=sys.stdin
  else:
    fp=open(sys.argv[1])

  alltiles = loadFile(fp)

  ofp_ant=open(antfilename,'w')
  ofp_inst=open(instrfilename,'w')

  inst_config = makeInstConfig(alltiles)
  ant_loc = makeAntLocations(alltiles)

  print >> ofp_ant, ant_loc,
  print >> ofp_inst,inst_config,

