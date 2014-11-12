#! /usr/bin/env python
"""

A python wrapper which goes from NGAS correlator files to uvfits divided into subbands as required for the RTS. Calls in order:
i) convert_ngas.py
ii) split_ngas_header.py 
iii) subbands_corr2uvfits_wrapper.py
iv) generate_RTS_in.py

"""

import sys, os

if (len(sys.argv) != 6):
    print 'Usage: python ngas2uvfitssubbandsRTS [basename] [data_dir] [gps] [# of subbands] [rts_templates]'
else:

    basename = str(sys.argv[1])
    data_dir = str(sys.argv[2])
    gpstime = str(sys.argv[3])
    n_subbands = int(sys.argv[4])
    rts_templates = str(sys.argv[5])

    cmd = "build_128T_lfiles.py %s  %s/*gpubox*.fits" % (basename, data_dir)
    print cmd
    os.system(cmd)

    cmd = "make_metafiles.py -l --gps=%s --dt 0.5 --df 40 --header=header.txt --antenna=antenna_locations.txt --instr=instr_config.txt" % (gpstime)
    print cmd
    os.system(cmd)    

    cmd = "split_ngas_header.py header.txt %s %d" % (basename, n_subbands)
    print cmd
    os.system(cmd)

    cmd = "cp /scratch/astronomy556/bpindor/danny_demo/instr_config_A3667.txt instr_config.txt"
    print cmd
    os.system(cmd)

    cmd = "subbands_corr2uvfits_wrapper.py %s %d 0" % (basename, n_subbands)
    print cmd
    os.system(cmd)


