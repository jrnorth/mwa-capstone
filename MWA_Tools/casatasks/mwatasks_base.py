import os.path
from odict import odict
if not globals().has_key('mytasks') :
  mytasks = odict()
if not globals().has_key('task_location') :
  task_location = odict()

if sys.path[1] != dir:
  sys.path.insert(1,dir)
mytasks['flagDC'] = 'Flag the \"DC Spikes\" in the MWA coarse channels'
task_location['flagDC'] = dir
tasksum['flagDC'] = mytasks['flagDC']
print sys.path
from flagDC_cli import  flagDC_cli as flagDC

if sys.path[1] != dir:
  sys.path.insert(1, dir)
mytasks['flagChanGaps'] = 'Flag the gaps between the MWA coarse channels'
task_location['flagChanGaps'] = dir
tasksum['flagChanGaps'] = mytasks['flagChanGaps']
from flagChanGaps_cli import  flagChanGaps_cli as flagChanGaps

if sys.path[1] != dir:
  sys.path.insert(1, dir)
mytasks['pbgain'] = 'Generate a primary beam image'
task_location['pbgain'] = dir
tasksum['pbgain'] = mytasks['pbgain']
from pbgain_cli import  pbgain_cli as pbgain


