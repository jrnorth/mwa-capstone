#! /usr/bin/env python
"""
A tool to change the local database connection

By default it finds the last mwa.conf file in your search path and modifies the \'dbhost\' entry

It then writes the output to ./mwa.conf or another file as specified


"""


# these are the different possible hosts that can be used for the database
_hosts={'mit': 'eor-db.mit.edu',
        'site': 'helios',
        'curtin': 'ngas01.ivec.org',
        'site-test': 'helios2.mwa128t.org'}
# different aliases for some of these
_aliases={'site': ['mro','helios'],
          'curtin': ['ngas','ngas01'],
          'site-test': ['test','lab','helios2']}

_output='./mwa.conf'


import logging, sys, os, glob, string, re, urllib, math, time
from optparse import OptionParser
import ConfigParser
import mwaconfig
import mwapy

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('change_db')
logger.setLevel(logging.WARNING)


################################################################################
def main():
    usage="Usage: %prog [options] <newhost>\n"
    usage+="""
    A tool to change the local database connection
    By default it finds the last mwa.conf file in your search path and modifies the \'dbhost\' entry
    If --local (default) it then writes the output to ./mwa.conf or another file as specified
    If --global it will try to update the last file in the search path
    """
    usage+="\t<newhost> is one of:\n\t%s" % print_hosts().replace('\n','\n\t')
    usage+="Can accept either the name or the aliases" 
    parser = OptionParser(usage=usage,version=mwapy.__version__)
    parser.add_option('-g','--global',dest="globalwrite",default=False,action='store_true',
                      help="Try to update the global config file? [default=%default]")
    parser.add_option('-l','--local',dest="globalwrite",default=False,action='store_false',
                      help="Do not try to update the global config file?")
    parser.add_option('-o','--output',dest="output",default=_output,
                      help="Output config file [default=%default]")
    parser.add_option('--test',action="store_true",dest="test",default=True,
                      help="Test database connection after change? [default=%default]")
    parser.add_option('--notest',action="store_false",dest="test",default=True,
                      help="Test database connection after change? [default=%default]")
    
    parser.add_option('-v','--verbose',action="store_true",dest="verbose",default=False,
                      help="Increase verbosity of output")
    
    
    (options, args) = parser.parse_args()
    
    if (options.verbose):
        logger.setLevel(logging.INFO)
        
        
    newhost=None

    for arg in args:
        if arg.lower() in _hosts.keys():
            newhost=arg.lower()
        else:
            for host in _aliases.keys():
                if arg.lower() in _aliases[host]:
                    newhost=host
        if newhost is None:
            logger.error('No matching database host identified for \"%s\"' % arg)
            logger.error('Possible hosts:\n%s' % print_hosts())

    if newhost is None:
        logger.error('No database host given')
        logger.error('Possible hosts:\n%s' % print_hosts())
        sys.exit(1)

    logger.info('Will change host to %s (%s)' % (newhost,_hosts[newhost]))

    # get the last config file in the list, and change that one
    lastconfigfile=mwaconfig.CPfile[-1]
    CP = ConfigParser.SafeConfigParser(defaults={})
    CP.read(lastconfigfile)
    if options.globalwrite:
        options.output=lastconfigfile
    # write into default section
    CP.set('','dbhost',_hosts[newhost])
    try:
        f=open(options.output,'w')
    except IOError:
        logger.error('Unable to open %s for writing' % (options.output))
        sys.exit(1)
    CP.write(f)
    f.close()
    logger.info('Wrote %s with dbhost=%s' % (options.output,_hosts[newhost]))

    # reproduce a bit of mwaconfig to reload things here
    CP = ConfigParser.SafeConfigParser(defaults={})
    CPfile = CP.read(mwaconfig.CPpath)
    if not CPfile:
        print "None of the specified configuration files found by mwaconfig.py: %s" % (CPpath,)
    for _s in CP.sections():
        for _name,_value in CP.items(_s):
            setattr(mwaconfig.__dict__[_s],_name,_value)

    dbuser = mwaconfig.mandc.dbuser
    dbpassword = mwaconfig.mandc.dbpass
    dbhost = mwaconfig.mandc.dbhost
    dbname = mwaconfig.mandc.dbname

    logger.info('DB setup:\n\tdbuser = %s\n\tdbpassword = %s\n\tdbhost = %s\n\tdbname = %s\n' % (
        dbuser,dbpassword,dbhost,dbname))
    if options.test:
        logger.info('Testing connection to database...')
        # open up database connection
        from mwapy.obssched.base import schedule
        try:
            db = schedule.getdb()
        except:
            logger.error("Unable to open connection to database")
            sys.exit(1)
        logger.info('Connected!')


    sys.exit(0)

################################################################################
def print_hosts():
    s=''
    for h in _hosts.keys():
        s+='%s' % h
        if h in _aliases.keys():
            s+=' (%s)' % (','.join(_aliases[h]))
        s+=': %s\n' % _hosts[h]
    return s

################################################################################
    
if __name__=="__main__":
    main()
