
all: mwatasks.py

mytasks_flagDC.py flagDC_cli.py: task_flagDC.py
	buildmytasks flagDC; mv mytasks.py mytasks_flagDC.py;

mytasks_flagChanGaps.py flagChanGaps_cli.py: task_flagChanGaps.py
	buildmytasks flagChanGaps; mv mytasks.py mytasks_flagChanGaps.py;

mytasks_pbgain.py: task_pbgain.py
	buildmytasks pbgain; mv mytasks.py mytasks_pbgain.py;

mwatasks.py: mytasks_flagDC.py flagDC_cli.py mytasks_flagChanGaps.py flagChanGaps_cli.py mytasks_pbgain.py pbgain_cli.py
	echo "dir='$(PWD)'" > mwatasks.py;cat mwatasks_base.py >> mwatasks.py

clean:
	rm -f mytasks*.py mytasks*.py *_cli* mytasks*.py *_cli* mytasks*.py mytasks*.py mwatasks.py *-e
