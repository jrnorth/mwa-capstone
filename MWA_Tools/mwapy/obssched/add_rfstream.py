#!/usr/bin/env python
import psycopg2
import os, sys, optparse, logging

def main():
    logging.basicConfig(format='%(levelname)s: %(message)s')    

    usage="usage: %prog [options]"

    parser=optparse.OptionParser(usage=usage)

    parser.add_option("-g","--gps",dest="gpstime", default=None,type="int",
                      help="GPStime (observation ID) to lookup")
    parser.add_option("-t","--tile",dest="tileset",default=None,
                      help="Tileset for new RFstream")
    parser.add_option('-d','--delays',dest='delays',default=','.join(['0'] * 16),
                      help="Delays for new RFstream [default=%default]")
    parser.add_option("-v","--verbose",dest="verbose",default=False,action="store_true",
                      help="More verbose output?")
    parser.add_option("-q","--quiet",dest="verbose",default=False,action="store_false",
                      help="Less verbose output?")
    parser.add_option("--nodb",dest="nodb",default=False,action="store_true",
                      help="Do not write to database (for testing)")

    (options,args)=parser.parse_args()

    add_rfstream(gpstime=options.gpstime, newtiles=options.tileset, newdelays=options.delays)
    
    print 'RFStream successfully added!'
    
def add_rfstream(gpstime, newtiles, newdelays):

    conn = psycopg2.connect(database='mwa', user='mwa', host='helios.mwa128t.org', password='BowTie')
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
    
    try:
        cur = conn.cursor()
        cur.execute("select * from rf_stream where starttime = %s;", [str(gpstime),])
        rows = cur.fetchall()
        
        number = 0
        if len(rows) > 0:
            number = len(rows)
            cur.execute("insert into rf_stream (starttime, number, tile_selection, hex, azimuth, elevation, ra, dec, frequencies, gain_control_type, gain_control_value, frequency_type, walsh_mode, vsib_frequency) \
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);", \
                        [str(gpstime), number, newtiles, newdelays, \
                         None if not rows[0][2] else str(rows[0][2]), None if not rows[0][3] else str(rows[0][3]), None if not rows[0][4] else str(rows[0][4]), None if not rows[0][5] else str(rows[0][5]), None if not rows[0][8] else str(rows[0][8]).replace('[', '{').replace(']', '}'), str(rows[0][10]), str(rows[0][11]), str(rows[0][15]), str(rows[0][9]), None if not rows[0][16] else str(rows[0][16]) ])
        else:
            cur.execute("insert into rf_stream (starttime, number, tile_selection, hex) values (%s, %s, %s, %s);", [str(gpstime), number, newtiles, newdelays])
        
    except Exception as e:    
        conn.rollback()
        raise e
    else:
        conn.commit()
    
if __name__=="__main__":
    main()

