#run with casapy --nologger -c casacal2npz.py *.cal
import numpy as n
for i in range(len(sys.argv)):
    if sys.argv[i]==inspect.getfile( inspect.currentframe()):break
for calfile in sys.argv[i+1:]:
    outfile = calfile[:-4]+'.npz'
    print calfile, "-->",outfile
    tb.open(calfile)
    try: G = tb.getcol('GAIN')
    except: G = tb.getcol('CPARAM')
    M = tb.getcol('FLAG')
    SNR = tb.getcol('SNR')
    tb.close()
    tb.open(calfile+'/SPECTRAL_WINDOW')
    freqs = tb.getcol('CHAN_FREQ').squeeze()/1.e6
    n.savez(outfile,G=G,SNR=SNR,mask=M,freq=freqs)

