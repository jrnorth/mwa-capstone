#! /usr/bin/env python

_START_128T=1046304456

def parse_auto_flags(gps):

    import os

    mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')

    infile = mwa_dir + 'MWA_Tools/scripts/auto_flag.py'
    in_file = open(infile)

    in_range = 0

    tile_list = []

    for line in in_file:
        i1 = line.find('obsnum>')
        i2 = line.find('obsnum<=')
        if(i1>0):
            gps1 = int(line[i1+7:i1+17])
            if(i2>0):
                gps2 = int(line[i2+8:i2+18])
            else:
                gps2 = 2000000000

            if(gps > gps1 and gps < gps2):
                in_range = 1
            else:
                in_range = 0

        if(in_range):
            ant_p = line.find('antenna=')
            if(ant_p > 0):
                antenna_i = line[ant_p+9:ant_p+16]
                tile_list.append(antenna_i)

    return tile_list
    in_file.close()

def parse_instr_config(data_dir):


    infile = data_dir + '/instr_config.txt'
    in_file = open(infile)   

    tile_list = []

    for line in in_file:
        if(line.find('1 #') > 0):
            tile = line.split()[-1]
            if not (tile in tile_list):
                tile_list.append(tile)

    return tile_list

###

import sys, os

if (len(sys.argv) != 2):
    print 'Usage: auto_flag_rts.py [gps]'
else:
            
    gps = sys.argv[1]

    mwa_dir = os.getenv('MWA_DIR','/scratch/astronomy556/MWA/')
    data_dir = mwa_dir + 'data/' + gps

    if(gps >= _START_128T):

        tile_list = parse_instr_config(data_dir)

        antennafile = mwa_dir + 'data/' + gps + '/antenna_locations.txt'
        try:
            antenna_file = open(antennafile)
        except IOError, err:
            'Cannot open antenna locations file %s\n' % antennafile
            sys.exit(1)

        flagsfile = mwa_dir + 'data/'  + gps + '/flagged_tiles.txt'
        flags_file = open(flagsfile,"w")

        tile_count = 0
        for line in antenna_file:
            if(line.find('#')!=0):
                tile = (line.split())[0]
                for flag_tile in tile_list:
                    if(flag_tile == tile):
                        flags_file.write('%d\n' % tile_count)
                tile_count += 1
        antenna_file.close()

        flags_file.close()
        
        

#        rts_dir = mwa_dir + 'RTS/utils/flags/'
#        default_tile_flags = rts_dir + 'flagged_tiles_128T_default.txt'
#        default_channel_flags = rts_dir + 'flagged_channels_128T_default.txt'
#        os.system('cp %s %s/flagged_tiles.txt' % (default_tile_flags, data_dir))
#        os.system('cp %s %s/flagged_channels.txt' % (default_channel_flags, data_dir))

    else:

        tile_list = parse_auto_flags(int(gps))            

#        print tile_list

        antennafile = mwa_dir + 'data/' + gps + '/antenna_locations.txt'
        try:
            antenna_file = open(antennafile)
        except IOError, err:
            'Cannot open antenna locations file %s\n' % antennafile
            sys.exit(1)

        flagsfile = mwa_dir + 'data/'  + gps + '/flagged_tiles.txt'
        flags_file = open(flagsfile,"w")

        tile_count = 0
        for line in antenna_file:
            if(line.find('#')!=0):
                tile = (line.split())[0]
                for flag_tile in tile_list:
                    if(flag_tile == tile):
                        flags_file.write('%d\n' % tile_count)
                    tile_count += 1
        antenna_file.close()

        flags_file.close()
            
