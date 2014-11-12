#! /usr/bin/env python

import sys,os,glob
import pyfits
import subprocess
from optparse import OptionParser,OptionGroup

def match_cal_name(fieldname,sourceCat):

	rts_dir = os.getenv('RTSDIR','/scratch/astronomy556/MWA/RTS/')
	cals_file = open(rts_dir + 'utils/source_lists/MWA_Cals_Match.txt')

	objname = fieldname.split('_')[1]

	cal_name = None

	for line in cals_file:
		if(line.split()[0] == objname):
			if(sourceCat == 'srclist_culgoora_mod.txt'):
				cal_name = line.split()[3]
			if(sourceCat == 'pks.txt'):
				cal_name =  line.split()[1]

	return cal_name


"""
generate_RTS_in.py
Takes as input header.txt file created by convert_ngas and generates rts .in files 
"""

import sys,os,glob
import subprocess
from optparse import OptionParser,OptionGroup
from math import sin, cos, atan2, asin, degrees, radians 

mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')

usage= 'Usage: generate_RTS_in_mwac.py [data_dir] [input_file] [basename] [# of subbands] [array]\n'
usage+= 'Generate RTS .in files for use in fornax RTS pipeline\n'

parser = OptionParser(usage=usage)

parser.add_option('--header',dest="input_file",default='header.txt',
                      help="corr2uvfits style header file",metavar="DATADIR")
parser.add_option('--templates',dest="template_list",default=None,
                      help="List of RTS template file",metavar="RTSLIST")
parser.add_option('--channel_flags',dest="channel_flags",default=mwa_dir + '/RTS/utils/flags/flagged_channels_default.txt',
                      help="File containing flagged channels",metavar="CHANNELFLAGS")

(options, args) = parser.parse_args()


data_dir = args[0]
basename = args[1]
n_subbands = int(args[2])
array = str(args[3])

half_channelwidth = 0.02 # 20 khz

if not (array == '32T' or array == '128T'):
        print 'Array Parameter should be \'32T\' or \'128T\''
        exit(1)

# Read in list of RTS template files

if options.template_list is None:
    template_files = [mwa_dir + 'RTS/utils/templates/RTS_template_regrid.in']
else:
    try: 
        template_list_file = open(options.template_list)
    except IOError, err:
        'Cannot open list of RTS template files %s\n' % str(options.template_list)
        
    template_files = []
    for line in template_list_file:
        template_files.append(line.strip())
    template_list_file.close()

# Set channel flag file

    cmd = 'cp %s flagged_channels.txt' % (options.channel_flags)
    os.system(cmd)

# Read in corr2uvfits style header file

if(options.input_file=='header.txt'):

	try:
		in_file = open(options.input_file)
	except IOError, err:
		'Cannot open header file %s\n' % str(options.input_file)

	for line in in_file:
	     if(line.find('N_CHANS')==0):
		 n_chans = int((line.split())[1])
	     if(line.find('N_SCANS')==0):
		 n_scans = int((line.split())[1])
	     if(line.find('INT_TIME')==0):
		 int_time = float((line.split())[1])
	     if(line.find('BANDWIDTH')==0):
		 full_bandwidth = float((line.split())[1])
		 bandwidth = full_bandwidth / float(n_subbands)
		 half_channelwidth = (full_bandwidth / (n_chans * 2.0)) / 1000.0 
	     if(line.find('FREQCENT')==0):
		 freq_cent = float((line.split())[1])
	     if(line.find('HA_HRS')==0):
		 ha_point = float((line.split())[1])
		 if(ha_point > 12.0):
		     ha_point -= 24.0
	     if(line.find('DEC_DEGS')==0):
		 dec_phase = float((line.split())[1])
		 dec_point = dec_phase
	     if(line.find('RA_HRS')==0):
		 ra_phase = float((line.split())[1])
	     if(line.find('FIELDNAME')==0):
		 fieldname = ((line.split())[1])


	in_file.close()


	

else:
	try:
		in_file = pyfits.open(options.input_file)
	except IOError, err:
		'Cannot open metadata file %s\n' % str(options.input_file)

	n_chans = int((in_file[0].header)['NCHANS'])
	n_scans = int((in_file[0].header)['NSCANS'])
	int_time = float((in_file[0].header)['INTTIME'])
	full_bandwidth = float((in_file[0].header)['BANDWDTH'])
	bandwidth = full_bandwidth / float(n_subbands)
	freq_cent = float((in_file[0].header)['FREQCENT'])
	ra_point = float((in_file[0].header)['RA'])
	dec_point = float((in_file[0].header)['DEC'])
	ra_phase = float((in_file[0].header)['RAPHASE'])
	ra_phase = ra_phase / 15.0 # Convert to hrs
	dec_phase = float((in_file[0].header)['DECPHASE'])
	lst = float((in_file[0].header)['LST'])
	ha_point = (lst - ra_point) / 15.0
	fieldname = (in_file[0].header)['FILENAME']
	finechan = float((in_file[0].header)['FINECHAN'])
	half_channelwidth = (finechan / 2.0) / 1000.0
	az = radians(float((in_file[0].header)['AZIMUTH']))
	el = radians(float((in_file[0].header)['ALTITUDE'])) 
	lat = -26.70331940 # Check this??
	lat = radians(lat)

	ha_point = degrees(atan2( -sin(az)*cos(el), cos(lat)*sin(el)-sin(lat)*cos(el)*cos(az))) / 15.0
        dec_point = degrees(asin( sin(lat)*sin(el)+cos(lat)*cos(el)*cos(az) ))

	in_file.close()
	
	

##


rts_file_index = 0

# How many GPU boxes are there?

gpu_files = glob.glob(data_dir + '/*gpubox*00.fits')  

if(len(gpu_files) > 0):
	#band_list = [int(filename[filename.find('gpubox')+6:-8]) for filename in gpu_files] 
	band_list = [int(filename[-10:-8]) for filename in gpu_files]

else:
	uvfile_list = glob.glob(data_dir + '/*uvfits')
	band_list = [int(filename[-9:-7]) for filename in uvfile_list]   

band_list.sort()

subband_string = ''

for band in band_list:
    subband_string = subband_string + str(band) + ','

subband_string = subband_string[:-1]

for file in template_files:

    template_file = open(file)

    outfile = basename + ('_rts_%d.in' % rts_file_index)
    rts_file_index += 1

    out_file = open(outfile,"w+")
    set_subbands = 0

    # Check to make sure the template is of mwac type

    is_mwac = 0
    gps = data_dir[len(mwa_dir + 'data/'):]
    # strip trailing slash if necessary
    if(gps[-1] == '/'):
	    gps = gps[:-1]
    times = os.popen('timeconvert.py --gps=%s' % gps).read()
    jd = (times.split('\n')[5]).split()[1]
				    

    # Make first pass through template_file to:
    # i) work out imaging cadence
    # ii) check if we need to see the primary calibrator
    # iii) Are we reading directly from gpubox files

    CorrDumpTime = CorrDumpsPerCadence = -1.0
    usePrimaryCalibrator = False
    readGpuboxDirect = False

    for line in template_file:
	if(line.find('CorrDumpTime')==0):
		CorrDumpTime = float(line[len('CorrDumpTime='):])
	if(line.find('CorrDumpsPerCadence')==0):    
		CorrDumpsPerCadence = float(line[len('CorrDumpsPerCadence='):])
	if(line.find('PrimaryCalibrator')==0):
		usePrimaryCalibrator=True
	if(line.find('SourceCatalogueFile')==0):
		SourceCat = line[line.rfind('/')+1:-1]
	if(line.find('ReadGpuboxDirect=1')==0):
		readGpuboxDirect = True

    if(CorrDumpTime > 0 and CorrDumpsPerCadence):
	    imaging_cadence = CorrDumpTime * CorrDumpsPerCadence
    else:
	    imaging_cadence = 8.0 #default

    scan_time = n_scans * int_time
    n_iterations = int(scan_time / imaging_cadence)

    if(usePrimaryCalibrator):
	    PrimaryCalibrator = match_cal_name(fieldname,SourceCat)
	    

    template_file.close()

    # Now write new .in file

    template_file = open(file)

    for line in template_file:

        line_out = line
        if(line.find('BaseFilename')==0):
		line_out = 'BaseFilename=' + data_dir + '/*_gpubox' + '\n'
        if(line.find('NumberOfChannels')==0):
		line_out = line.replace(line[len('NumberOfChannels='):],str(n_chans/n_subbands) + '\n')
        if(line.find('ObservationFrequencyBase')==0):
            line_out = line.replace(line[len('ObservationFrequencyBase='):],str(freq_cent - full_bandwidth/2.0 - half_channelwidth) + '\n')
        if(line.find('ObservationPointCentreHA')==0):
            line_out = line.replace(line[len('ObservationPointCentreHA='):],str(ha_point) + '\n')
        if(line.find('ObservationPointCentreDec')==0):
            line_out = line.replace(line[len('ObservationPointCentreDec='):],str(dec_point) + '\n')
        if(line.find('ObservationImageCentreRA')==0):
            line_out = line.replace(line[len('ObservationImageCentreRA='):],str(ra_phase) + '\n')
        if(line.find('ObservationImageCentreDec')==0):
            line_out = line.replace(line[len('ObservationImageCentreDec='):],str(dec_phase) + '\n')
	
        if(line.find('NumberOfIterations')==0):
		if(array=='32T'):
			# CorrDumpsPerCadence is currently hard set to 4
			line_out = line.replace(line[len('NumberOfIterations='):],str(n_scans/4) + '\n')
		else:
			# Clip last iteration in case of missing data. TO DO: This is a hack.
			if(n_iterations > 2 and readGpuboxDirect==False):
				line_out = line.replace(line[len('NumberOfIterations='):],str(n_iterations-1) + '\n')
			else:
				line_out = line.replace(line[len('NumberOfIterations='):],str(n_iterations) + '\n')
        if(line.find('SubBandIDs=')==0):
		line_out = line.replace(line[len('SubBandIDs='):],subband_string + '\n')
		set_subbands = 1

	#MWAC

	if(line.find('UseCorrelatorInput=1')==0):
		is_mwac=1
	if(line.find('ObservationTimeBase=')==0):
		line_out = line.replace(line[len('ObservationTimeBase='):],jd + '\n')	
		
	# Primary calibrator

	if(line.find('PrimaryCalibrator')==0):
		line_out = line.replace(line[len('PrimaryCalibrator='):],PrimaryCalibrator + '\n')


        out_file.write(line_out)

	   
    if(array=='128T'):
        if(set_subbands == 0):
            out_file.write('SubBandIDs='+subband_string+'\n')
    out_file.close()
    template_file.close()


            
            
            
