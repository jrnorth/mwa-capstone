#modules from 32T_Tools
#import pb
#import catalog
#modules from MandC_Core/mwapy
#import config_local,data_files,dbobj
#try: import snmp,zeus
#except(ImportError): 
#    #print "pysnmp not found: modules that use mwapy.snmp will not be available."
#    pass
#import tspan
#possible troublemakers (zeus, snmp)

#new to MWA_Tools
#import delay_to_pointing,ephem_utils,get_observation_info,make_instr_config

try:
    from _version import __version__ as v
    __version__ = v
    del v
except ImportError:
    __version__ = "UNKNOWN"

try:
    from _version import __date__ as d
    __date__ = d
    del d
except ImportError:
    __date__ = "UNKNOWN"
