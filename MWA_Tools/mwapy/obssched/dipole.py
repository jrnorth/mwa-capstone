
import mwaconfig

from mwapy import dbobj

dbuser = mwaconfig.mandc.dbuser
dbpassword = mwaconfig.mandc.dbpass
dbhost = mwaconfig.mandc.dbhost
dbname = mwaconfig.mandc.dbname     #Use main science database

verbose = False

def getdb(user=dbuser, password=dbpassword, host=dbhost, database=dbname):
  """Returns a db object. This must be passed to all methods that interact
     with the database (__init__, save, getall, etc). A db object cannot
     be shared across threads, and after any changes to the database,
     db.commit() must be called to make these changes visible to other
     db objects or connections. If db.rollback() is called instead, all
     changes are discarded.
  """
  dbob = dbobj.getdb(user=user, password=password, host=host, database=database)
  return dbob


class DipoleState(dbobj.dbObject):
  _table = 'dipole_exclusion_table'
  _attribs = [('name','name',''),
              ('tile','tile',0),
              ('exclude_x_dipoles','exclude_x_dipoles',set([])),
              ('exclude_y_dipoles','exclude_y_dipoles',set([])) ]
  _key = ('tile',)
  _readonly = []
  _reprf = 'Dipole State[Tile %(tile)d]'
  _strf = 'Tile %(tile)d Exclude lists:\n'+                   \
          '    exclude_x_dipoles=%(exclude_x_dipoles)s\n' +   \
          '    exclude_y_dipoles=%(exclude_y_dipoles)s'
  _nmap = {}
  for oname,dname,dval in _attribs:
    _nmap[oname] = dname

  def tr_d2o(self,name,value):
    if name=='exclude_x_dipoles' or name=='exclude_y_dipoles':
      return set(value)      #psycopg2 does type conversion to a Python list, but we want a set
    else:
      return value

  def tr_o2d(self,name,value):
    if name=='exclude_x_dipoles' or name=='exclude_y_dipoles':
      return list(value)    #Convert to a list before passing to psycopg2, it handles conversion to the right SQL query
    else:
      return value

  def check(self, db=None, recursive=False):
    return []     #No tileset checking yet

  def save(self, ask=0, force=1, commit=1, verbose=0, db=None):
    """Save Dipole State object to database.
    """
    errors = self.check(db=db, recursive=False)
    if errors:
      if verbose:
        print "Object '%s' not saved due to errors." % self
      return errors
    dbobj.dbObject.save(self, ask=ask, force=force, commit=commit, verbose=0, db=db)
    if verbose:
      print "Object '%s' saved." % self
    return errors


def Toggle(db=None, tile=None, did=None, pol=None):
  """Given a tile, dipole ID (did), and polarisation (X or Y), toggle the enable/disable state
  """
  if tile and did and pol:
    ds = DipoleState(keyval=tile, db=db)
    retval = None
    if pol == 'X':
      if did in ds.exclude_x_dipoles:
        ds.exclude_x_dipoles.remove(did)
        retval = False
      else:
        ds.exclude_x_dipoles.add(did)
        retval = True
    if pol == 'Y':
      if did in ds.exclude_y_dipoles:
        ds.exclude_y_dipoles.remove(did)
        retval = False
      else:
        ds.exclude_y_dipoles.add(did)
        retval = True
    errors = ds.save(db=db)
    if errors:
      return None
    else:
      return retval

    
        

