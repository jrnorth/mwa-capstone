
import mwaconfig
from mwapy import dbobj, ephem_utils

class MWA_Source(dbobj.dbObject):
  _table = 'mwa_sources'
  _attribs = [('name','sourcename',''),
              ('ra','ra',None),
              ('dec','dec',None),
              ('sourceclass','sourceclass',''),
              ('moving','moving',False),
              ('notes','notes',''),
              ('creator','creator',''),
              ('modtime','modtime','')]
  _readonly = ['modtime']
  _key = ('name',)
  _reprf = 'MWA Source[%(name)s]'
  _strf = '%(name)s[%(sourceclass)s]: %(ra)s,%(dec)s, moving=%(moving)s, notes=%(notes)s' 
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

  def __str__(self):
      s = "%s[%s]:" % (self.name, self.sourceclass)
      if (not self.moving):
          s += " %s,%s" % (ephem_utils.dec2sexstring(self.ra/15.0), ephem_utils.dec2sexstring(self.dec,includesign=1))
      else:
          s += " (moving)"
      if (self.notes):
          s += ", notes=%s" % self.notes 
      return s

  def prompt(self):
      """prompt user to fill in data for a new source entry
      """
      print "\nDefining new MWA Source object:"
      if (not self.name):
          self.name = raw_input('Enter source name: ').strip()
      self.sourceclass = raw_input('Enter source class: ').strip()
      val = raw_input('Is the source moving[no]? ').strip()
      if (val.lower() in ('no','n','false','f')):
          self.moving = False
      elif (val.lower() in ('yes','y','true','t')):
          self.moving = True
      else:
          print "Invalid entry: assuming not moving"
          self.moving = False
      if (not self.moving):
          val = raw_input('Enter coordinate type (1=RA,Dec; 2=l,b)[1]: ').strip()
          if (not val):
              coord = 1
          else:
              try:
                  coord = int(val)
              except ValueError:
                  coord = 0
              if (coord != 1 and coord != 2):
                  print "Invalid entry: assuming RA,Dec"
                  coord = 1
          if (coord == 1):
              # RA/Dec
              val = raw_input('Enter RA (degrees or hh:mm:ss): ').strip()
              try:
                  if (val.count(':')>0):
                      self.ra = ephem_utils.sexstring2dec(val)*15
                  else:
                      self.ra = float(val)
              except:
                  print "Error parsing RA\n"
                  return
              val = raw_input('Enter Dec (degrees or dd:mm:ss): ').strip()
              try:
                  if (val.count(':')>0):
                      self.dec = ephem_utils.sexstring2dec(val)
                  else:
                      self.dec = float(val)
              except:
                  print "Error parsing Dec\n"
                  return
          else:
              # l/b
              val = raw_input('Enter l (degrees or dd:mm:ss): ').strip()
              try:
                  if (val.count(':')>0):
                      gall = ephem_utils.sexstring2dec(val)
                  else:
                      gall = float(val)
              except:
                  print "Error parsing l\n"
                  return
              val = raw_input('Enter b (degrees or dd:mm:ss): ').strip()
              try:
                  if (val.count(':')>0):
                      galb = ephem_utils.sexstring2dec(val)
                  else:
                      galb = float(val)
              except:
                  print "Error parsing b\n"
                  return
              [self.ra,self.dec] = ephem_utils.lbtoad(gall/ephem_utils.DEG_IN_RADIAN,galb/ephem_utils.DEG_IN_RADIAN)
              self.ra *= ephem_utils.DEG_IN_RADIAN
              self.dec *= ephem_utils.DEG_IN_RADIAN

      self.notes = raw_input("Enter notes: ").strip()        

      self.creator = raw_input("Enter creator name: ").strip()        



def verifyfields(db=None):
  """Check that database fields match _attrib definitions for all tables
     defined in classes, and print warning messages for any mismatch.
  """
  MWA_Source.verifyfields(db=db)



def getSources(db=None, dictform=False):
  """Return all MWA_Source objects in database, as a list or dict.
  """
  if dictform:
    return MWA_Source.getdict(db=db)
  else:
    return MWA_Source.getall(db=db)




