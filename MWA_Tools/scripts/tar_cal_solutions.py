#! /usr/bin/env python
import sys,os

infile = str(sys.argv[1])

in_file = open(infile)

cmd = 'tar -czf multi_cals.tar.gz'

mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')
data_dir = mwa_dir + 'data/'

for line in in_file:
    obsid = line.split()[0]
    cmd = cmd + '%s/*.dat %s/flagged* %s/*.log ' % (data_dir+obsid, data_dir+obsid, data_dir+obsid)

print cmd

os.system(cmd)
