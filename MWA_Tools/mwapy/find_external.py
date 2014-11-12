
import logging, sys, os, glob, subprocess, string, re, urllib, math, time

# configure the logging
logging.basicConfig(format='# %(levelname)s:%(name)s: %(message)s')
logger=logging.getLogger('find_external')
logger.setLevel(logging.WARNING)

def find_external(external_programs):
    # go through and find the external routines in the search path
    # or $MWA_PATH
    searchpath=os.environ.get('MWA_PATH')
    if (searchpath is not None):
        searchpath=searchpath.split(':')
    else:
        searchpath=[]
    searchpath.append(os.path.abspath(os.path.dirname(sys.argv[0])))
    external_paths={}
    for external_program in external_programs.keys():
        external_paths[external_program]=None
        p=subprocess.Popen('which %s' % external_program, shell=True,stderr=subprocess.PIPE,
                           stdout=subprocess.PIPE, close_fds=True)
        (result,result_error)=p.communicate()
        if (len(result) > 0):
            # it was found
            external_paths[external_program]=result.rstrip("\n")
        else:
            for path in searchpath:
                if (os.path.exists(path + '/' + external_program)):
                    external_paths[external_program]=path + '/' + external_program
        if (external_paths[external_program] is None):
            # was not found anywhere
            logger.warning('Unable to find external program %s; please set your MWA_PATH environment variable accordingly',external_program)
            if (external_programs[external_program]):
                logger.error('External program %s is required; exiting',external_program)
                sys.exit(1)
        else:
            logger.debug('Found %s=%s',external_program,external_paths[external_program])
    return external_paths
