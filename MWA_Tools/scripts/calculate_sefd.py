"""

# 2013/06/26

This script calculates the SEFD for each antenna as a function of frequency.

Input: calibrated CASA measurement set
Output: 2 .dat files for pols=(0,3)=(XX,YY) that list the antenna SEFDs for each fine frequency channel

Example usage:
   casapy --nologger -c calculate_sefd.py --t_int=4 --eta_s=0.8 --bad_tiles='11,15,27' <filename>.ms

"""

import sys,optparse
import numpy
from datetime import datetime

#######################################################

def gen_chan_list(freq_avg):
    """
    Generate list of fine channel numbers for SEFD calculation. 
    Skip channel gaps and DC channels.

    """
    chan_list=[]
    if freq_avg: 
        nfine_per_coarse=32  # 32 fine/coarse [40kHz]
        dc_offset=16
        chan_gap=8
    else:
        nfine_per_coarse=128  # 128 fine/coarse [10kHz]
        dc_offset=64
        chan_gap=48
    n_coarse=24  # number of coarse channels
    chan_offset=numpy.array(range(n_coarse))*nfine_per_coarse  # list of first fine channel number for each coarse channel
    dc_chan=numpy.array(range(n_coarse))*nfine_per_coarse+dc_offset  # list of DC channel numbers
    for first_fine_in_coarse in chan_offset:
        chan_range=range(first_fine_in_coarse+chan_gap, first_fine_in_coarse+nfine_per_coarse-chan_gap)  # skip channel gaps
        for ch in chan_range:
            if ch not in dc_chan:  # skip DC channel
                chan_list.append(ch)
    return chan_list

#######################################################

# create command line arguments
parser=optparse.OptionParser()
parser.set_usage("Usage: casapy [--nologger] -c calculate_sefd.py [options] <filename>.ms")
parser.add_option("--ntiles",dest="ntiles",default=32,
                  help="Total number of tiles, good and bad. [default: %default]")
parser.add_option("--t_int",dest="t_int",default=1,
                  help="Integration time in seconds, 100% correlator duty cycle. [default: %default]")
parser.add_option("--eta_s",dest="eta_s",default=1.0,
                  help="System efficiency factor to account for losses in electronics. [default: %default]")
parser.add_option("--bad_tiles",dest="bad_tiles",default='-1',
                  help="List of bad tiles to exclude. 1-indexed. [default: %default]")
parser.add_option("--bad_baselines",dest="bad_baselines",default='-1',
                  help="List of bad baselines to exclude (in CASA format). 1-indexed. [default: %default]")
parser.add_option("--freq_avg",dest="freq_avg",default=True,
                  help="False for 10kHz, True for 40kHz channels. [default: %default]")

# parse command line arguments
casa_index=sys.argv.index('-c')+2  # remove CASA options
(options,args)=parser.parse_args(sys.argv[casa_index:])
n_ant,t_int,eta_s=int(options.ntiles),float(options.t_int),float(options.eta_s)
freq_avg=options.freq_avg
bad_tiles=map(int,options.bad_tiles.split(','))  # tile numbers are 1-indexed
bad_baselines=options.bad_baselines.split(',')
input_ms=args[-1]  # calibrated CASA measurement set

# set variables
if freq_avg:
    n_chan=768  # number of fine frequency channels (40kHz)
    chan_width=40000  # fine channel width: 40kHz
else:
    n_chan=3072  # 10kHz
    chan_width=10000  # fine channel width: 10kHz
chan_list=gen_chan_list(freq_avg)
n_baseline=n_ant*(n_ant-1)/2  # number of baselines
pol=[0,3] #,'YY','XY','YX']  # polarization
polname=['XX','XY','YX','YY']  # CASA correlation order
ofname='sefd_'+input_ms[:-3]  # set output file namebase

# echo input parameters
print '='*50
print 'SEFDs calculated for '+input_ms
print 'Total number of antennas: %i'%(n_ant)
print 'Integration time (with 100%% duty cycle): %f sec'%(t_int)
print 'System efficiency: %f'%(eta_s)
print 'Using %i fine channels each with channel width %ikHz'%(n_chan,chan_width/1000)
print 'Excluding tiles '+str(bad_tiles)
print 'Excluding baselines '+str(bad_baselines)

# get channel frequency (MHz)
ms.open(input_ms)
ms.selectinit(datadescid=0)  # data description id
freq=ms.range('chan_freq')['chan_freq']/1e6
freq=numpy.squeeze(freq)
ms.close()

# delete autocorrelation baseline rows
baseline_index = []
n_vis=n_baseline+n_ant  # number of visibility data points per time integration
for b in range(n_vis):
    baseline_index.append(b)
baseline_index = numpy.array(baseline_index)
i=0      # autocorr baseline row to drop
j=n_ant  # increment to next autocorr baseline
while j > 0:
    baseline_index=numpy.delete(baseline_index,i)
    j=j-1
    i=i+j

# read visibility data
ms.open(input_ms)
for p in pol:

    # create file to save sefd output
    # output: (row,column)=(m,k) is the sefd at frequency m for antenna k
    filename=ofname+'_'+str(polname[p])+'.dat'
    print 'SEFDs for pol '+str(polname[p])+' will be written to '+filename
    print 'Computing for '+str(polname[p])+'...'

    for ch in chan_list:

        print '  channel %i...'%ch

        # reset variables for each frequency channel
        print 'READ DATA: ' + str(datetime.now())
        b=0
        stddev_vector=numpy.zeros((n_baseline,1))
        corr_matrix=numpy.zeros((n_baseline,n_ant))
        ms.selectchannel(1,ch,1,1)
        calvis_imag = ms.getdata(['corrected_data'])['corrected_data'][p,0,:].imag
        n_scans=calvis_imag.shape[0]/n_vis  # number of time integrations in this observation

        # iterate over antennas (0-indexed)
        print 'FILL MATRIX: ' + str(datetime.now())
        for i in range(n_ant):

            j=i+1
            while j < n_ant:
                
                # for each baseline i-j (1-indexed)
                baseline='%i&%i'%(i+1,j+1)
                if not ((i+1 in bad_tiles) or (j+1 in bad_tiles) or (baseline in bad_baselines)):
                    
                    ##### for valid baselines #####

                    # calculate standard deviation (ms.statistics['stddev'] same as numpy.std(ddof=1), i.e. 1/sqrt(n-1) factor and not 1/sqrt(n))
                    calvis=[]
                    for t in range(n_scans):
                        # get visibilities for baseline b at all times
                        calvis.append(calvis_imag[baseline_index[b]+t*n_vis])
                    calvis = numpy.array(calvis)
                    stddev=numpy.std(calvis,ddof=1)

                    if stddev != 0 and numpy.isfinite(stddev):
                    
                        ## treat funky stddev values as bad baselines ##
                        # construct stddev vector and 'correlation' matrix
                        stddev_vector[b,0]=2*log(eta_s*stddev*sqrt(2*chan_width*t_int))
                        corr_matrix[b,i]=1
                        corr_matrix[b,j]=1

                # while loop reset/increment
                b=b+1  # next matrix row
                j=j+1

        # set svd cutoff based on machine precision
        svd_cond=n_baseline*numpy.finfo(numpy.float).eps  # svd cutoff (1.10134124043e-13)

        # calculate sefd and the errors on sefd
        # use single value decomposition (svd)
        # the code below reproduces linalg.pinv
        print 'START INVERSION: ' + str(datetime.now())
        u,w,v=numpy.linalg.svd(corr_matrix,full_matrices=False)
        vT=v.transpose()
        uT=u.transpose()
        w[w < (numpy.max(w)*svd_cond)]=0  # svd cutoff
        w_inv=1/w
        w_inv[numpy.isinf(w_inv)]=0  # svd: replace 1/0 by 0

        # define sefd/error for antenna i, 0-indexed
        log_sefd=0
        log_sigma_sq=0
        udotb = numpy.dot(uT, stddev_vector[:,0])
        log_sefd = numpy.inner(vT, w_inv*udotb)
        log_sigma_sq = ((vT*w_inv)**2).sum(axis=1)

        # system is linear in log-space
        # propagate error back into normal space
        sefd=numpy.exp(log_sefd)
        sigma=sefd*numpy.sqrt(log_sigma_sq)
        print 'END INVERSION: ' + str(datetime.now())

        # write sefd to file
        # FREQ (MHz) | SEFD (Jy) | ERROR (Jy)
        outfile=open(filename,'a')
        outfile.write('\n%f\t'%freq[ch])
        outfile.write("\t".join(map(str, sefd)))
        outfile.write("\t")
        outfile.write("\t".join(map(str, sigma)))
        outfile.close()
        #print sefd, sigma

# close
ms.close()
