#! /usr/bin/env python
"""
Given a list of obsid directories with RTS cal solutions, produce
a series of calibration diagnostics.
summarize_RTS_cal.py 
"""
import numpy as n, sys,optparse,os
from pylab import *
from glob import glob
#import atpy
o = optparse.OptionParser()
#a.scripting.add_standard_options(o, cal=True,src=True)
#o.add_option('-r',dest='radius',default=10.,type='float',
#    help="Analysis region around brightest source [default 10 deg]")
opts, args = o.parse_args(sys.argv[1:])


def load_RTS_bp(F):
    """
    Loads an RTS cal
    """
    cal = n.zeros((4,32,128)).astype(n.complex128)
    lsq = n.zeros((4,32,128)).astype(n.complex128)
    if not os.path.exists(F):
        return cal,n.zeros_like(cal),n.zeros(32)
    lines = open(F).readlines()
    freqs = n.array(map(float,lines[0].strip().split(',')))
    chans = (freqs/0.04).astype(int)
    nfreqs = len(freqs)
    lines = lines[1:]
    for ant in range(128):
        antlines = []
        #scan through and get all lines for antenna i
        for line in lines:
            if line.startswith(str(ant)):
                antlines.append(line)
        if len(antlines)==0:
            continue
        for pol in n.arange(4):
            #parse Mitch's cal line
            D = n.array([map(float,l.split(',')) for l in antlines[pol*2].split(', ')[1:]])
            D.shape = (D.size/2, 2)
            D = D[:,0] + D[:,1]*1j
            L = n.array([map(float,l.split(',')) for l in antlines[pol*2+1].split(', ')[1:]])
            L.shape = (L.size/2,2)
            L = L[:,0] + L[:,1]*1j
            lsq[pol,chans,ant] = L
            cal[pol,chans,ant]= D
        SNR = lsq
        N = n.abs(lsq - cal)
        SNR[N>0] /= N[N>0] #fit-val as proxy for cal error 
    return cal,SNR,freqs
def line2mat(l):
    B = n.array(map(float,l.split(', ')))
    B.shape = (B.shape[0]/2,2)
    B = B[:,0] + B[:,1]*1j
    B.shape = (2,2)
    return n.matrix(B)

def load_RTS_antgain(F):
    amp = n.matrix(n.zeros((2,2)))
    if not os.path.exists(F):
        return [amp]*128
    lines = open(F).readlines()
    B = line2mat(lines[1])
    amps = []
    for i in range(2,128+2):
        gain = line2mat(lines[i])*B.I
        amps.append(gain)
    return amps



def load_RTS_mask(obsid):
    flagged_tiles = n.loadtxt('%s/flagged_tiles.txt'%obsid,dtype=int)
    flagged_chans = n.loadtxt('%s/flagged_channels.txt'%obsid,dtype=int)
    M = n.zeros((4,768,128))
    print flagged_tiles
    M[:,:,flagged_tiles] = 1
    M.shape = (4,24,32,128)
    flagged_chans = flagged_chans[flagged_chans<32]
    print flagged_chans
    M[:,:,flagged_chans,:] = 1
    M.shape = (4,768,128)
    return M
df = 0.04  #spacing of fine channels
coarse_size = 1.28 #spacing of coarse channels 
#grab all the obsid files
obsids = []
for F in args:
    obsids += [l.strip() for l in open(F).readlines()]
obsids = list(set(obsids))
for obsid in obsids:
    if not os.path.exists(obsid): 
        print obsid,"not found. Skipping"
        continue
    bandcals = []
    freqs = []
    for coarse_chan in range(1,25):
        #load the RTS cal solutions
        bpfile = '%s/BandpassCalibration_node%03d.dat'%(obsid,coarse_chan)
        print bpfile
        mybp,SNR,chans = load_RTS_bp(bpfile)
        G = n.zeros((2,768,128))
        antgainfile = '%s/DI_JonesMatrices_node%03d.dat'%(obsid,coarse_chan)
        print antgainfile
        myants = load_RTS_antgain(antgainfile)
        #cycle through each fine channel,antenna pair and multiply the 
        #antenna gains by the channel gains
        for ant in range(128):
            for chan in range(32):
                G_nu = n.matrix(mybp[:,chan,ant])
                G_nu.shape = (2,2)
                G_ant = myants[ant]
                myg = (G_ant * G_nu)
                G[:,chan,ant] = n.array([myg[0,0],myg[1,1]])#G_ant * G_bp according to Mitch
        bandcals.append(G)
        freqs.append(coarse_size*coarse_chan+chans)
    allgain = n.concatenate(bandcals,axis=1)
    M = load_RTS_mask(obsid)
    n.savez('%s/%s_RTS_cal.npz'%(obsid,obsid),SNR=SNR,G=allgain,mask=M,freq=n.arange(768)*0.04)
