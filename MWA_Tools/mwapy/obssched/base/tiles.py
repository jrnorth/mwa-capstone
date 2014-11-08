

class TileSpecError:
  def __init__(self,value):
    self.value=value
  def __str__(self):
    return `self.value`


def rtiles(tilespec=""):
  """Given a tile specifier (eg "1x, 2y, 3-8xy"), return a tuple 
     containing (xset,yset), where xset and yset are sets 
     (for X and Y polarisation respectively) of integer tile
     numbers.

     The format is a series of space or comma separated specifiers,
     each of which has the form of a number or number span (eg "3"
     or "25-30"), followed by "x", "y", "xy", or no polarisation 
     specifier (implying "xy"). Examples include:
       1x, 2y, 3-8xy
       1-32x, 1-30y
       10 11 12 13x, 14y
  """
  xset = set()
  yset = set()
  if (type(tilespec) <> type('')) or tilespec == "":
    raise TileSpecError("Empty tile specifier")
  speclist = tilespec.lower().replace(',',' ').split()
  for spec in speclist:
    if spec.endswith('xy') or spec.endswith('yx'):
      rng,pol = spec[:-2], 'xy'
    elif spec.endswith('x') or spec.endswith('y'):
      rng,pol = spec[:-1], spec[-1]
    else:
      rng,pol = spec, 'xy'
    
    n = rng.count('-')
    if n == 0:
      try:
        numlist = [int(rng)]
      except ValueError:
        raise TileSpecError("Invalid tile number: '"+rng+"'")
    elif n == 1:
      fr,to = rng.split('-')
      try:
        numlist = range(int(fr),int(to)+1)
      except ValueError:
        raise TileSpecError("Invalid tile number in: '"+rng+"'")
    elif n > 1:
      raise TileSpecError("Invalid tile range in: '"+rng+"'")

    for t in numlist:
      if (pol == 'x') or (pol == 'xy'):
        xset.add(t)
      if (pol == 'y') or (pol == 'xy'):
        yset.add(t)
  return xset,yset


def toranges(tlist=[]):
  """Given a list of tile numbers, group them into ranges.
  """
  if not tlist:
    return []
  tlist = list(tlist)
  tlist.sort()
  if len(tlist) == 1:
    return [(tlist[0],tlist[0])]
  ranges = []
  startt = tlist[0]
  for i in range(1,len(tlist)):
    if (tlist[i] <> tlist[i-1]+1):
      ranges.append((startt,tlist[i-1]))
      startt = tlist[i]
    if i == len(tlist)-1:
      ranges.append((startt,tlist[i]))
  return ranges


def tostring(t=(0,0)):
  tfrom,tto = t
  if tfrom == tto:
    return `tfrom`
  else:
    return `tfrom`+'-'+`tto`


def ftiles(xlist=[], ylist=[]):
  """Given xlist and ylist, generate a text tilespec that describes those tiles.
  """
  xranges = toranges(xlist)
  yranges = toranges(ylist)
  branges = []
  for r in xranges:
    if r in yranges:
      branges.append(r)
  for r in branges:
      xranges.remove(r)
      yranges.remove(r)
  outs = []
  for r in branges:
    outs.append(tostring(r)+'xy')
  for r in xranges:
    outs.append(tostring(r)+'x')
  for r in yranges:
    outs.append(tostring(r)+'y')
  return ','.join(outs)

  


