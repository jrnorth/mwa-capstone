#! /usr/bin/env python
"""
split_nag_header.py
Takes as input header.txt file created by convert_ngas and generates subband header files as well as rts .in files 
"""

import sys

if (len(sys.argv) != 4):
    print 'Usage: python split_ngas_header [input_file] [output_filenames] [# of subbands]'
else:
    try:
        in_file = open(str(sys.argv[1]))
    except IOError, err:
        'Cannot open header file %s\n',str(sys.argv[1])
        
    outFilename = str(sys.argv[2])
    n_subbands = int(sys.argv[3])

#    bandwidth = 30.72 / (float)(n_subbands)
    bandwidth = full_bandwidth = freq_cent = n_chans = ha_hrs = 0

    if(n_subbands==1):
        print 'No additional processing required for 1 subband'
    else:
        if((n_subbands % 4 !=0) or (n_subbands > 768)):
            print 'Number of subbands should be a number divisible by 4 and less than 768\n'
            sys.exit(1)

    fid = [open('%s_header_band%d.txt' % (outFilename,index), 'w+') for index in range(1, n_subbands+1)]  

    # First read some parameter values

    for line in in_file:
         if(line.find('N_CHANS')==0):
                n_chans = int((line.split())[1])
         if(line.find('BANDWIDTH')==0):
                full_bandwidth = float((line.split())[1])
                bandwidth = full_bandwidth / float(n_subbands)
         if(line.find('FREQCENT')==0):
                freq_cent = float((line.split())[1])
         if(line.find('HA_HRS')==0):
                ha_hrs = float((line.split())[1])
                if(ha_hrs > 12.0):
                    ha_hrs -= 24.0

    # Now go back to the beginning of the header file

    in_file.seek(0)    
        
    for line in in_file:

        line_out = line
        if(line.find('N_CHANS')==0):
            line_out = line.replace(str(n_chans),str(n_chans/n_subbands))
        if(line.find('BANDWIDTH')==0):
            line_out = line.replace((line.split())[1],str(bandwidth))
        if(line.find('RA_HRS')==0):
            line_out = line.replace((line.split())[1],str(ha_hrs + float((line.split())[1])))
        if(line.find('HA_HRS')==0):
            line_out = 'HA_HRS    0.0000 # Phase to zenith\n'
        if(line.find('DEC_DEGS')==0):
            line_out = line.replace((line.split())[1],'-26.70331940')
        for i,fp in enumerate(fid):
            if(line.find('FREQCENT')==0):
                line_out = line.replace((line.split())[1],str(freq_cent - 0.5 * full_bandwidth + (float(i + 0.5) * bandwidth )))

            fp.write(line_out)
                
    in_file.close()

    for fp in fid:
        fp.close()



    
                                        
            
            

    
    
