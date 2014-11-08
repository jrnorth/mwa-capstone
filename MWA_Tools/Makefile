# Makefile for corr2uvfits.
INCS=-I$(SIM_INC) -I/usr/include/cfitsio
CFLAGS=-g -O -Wall $(INCS) -D_FILE_OFFSET_BITS=64 -L.

TARGETS=casa #mwacalc

all: casa

casa: 
	cd casatasks; make
clean:
	cd CONV2UVFITS; make clean
	cd casatasks; make clean
	cd build_lfiles; make clean
	cd cfitsio; make clean
