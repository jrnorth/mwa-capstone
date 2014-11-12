#! /usr/bin/env python
import sys
for F in sys.argv[1:]:
    try:
        obsid = open(F).readlines()[0].strip()
        log = open(F).read()
        log = log.split('Choosing a cal source(s)')[1]
        log = log.split('done')[0]
        print "... - .- .-. -"
        print "--- -... ... .. -.."
        print obsid
        print ". -. -.."
        print "-.-. .- .-.. .. -... .-. .- - --- .-."
        print log.strip()
        print ". -. -.."
        print "... - --- .--."
    except(IndexError):
        continue
