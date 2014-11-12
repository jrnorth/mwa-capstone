import os
from glob import glob
from numpy.distutils.core import setup, Command
from distutils.command.install import install as DistutilsInstall
from distutils.sysconfig import get_python_lib,EXEC_PREFIX
from subprocess import call
import subprocess, re
from distutils.command.sdist import sdist as _sdist
from numpy.distutils.core import Extension

#check for required modules
try:
    try:
        import astropy.io.fits as pyfits
    except ImportError:
        import pyfits
    import ephem
    import pytz
    import pylab
    import psycopg2
except ImportError,e:
    print "ERROR! You are missing a dependency!"
    print e
    raise


v=pylab.matplotlib.__version__.split('.')
if float('.'.join(v[:2])) < 1.1:
    print "WARNING: matplotlib version > 1.1 recommended, and you have ",pylab.matplotlib.__version__


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()
packages = ['mwapy', 'mwapy.pb', 'mwapy.obssched', 'mwapy.catalog', 'mwapy.obssched.base', 'mwapy.obssched.utils', 'mwapy.eorpy']
#pythonlib=get_python_lib()
pythonlib=EXEC_PREFIX
print pythonlib

VERSION_PY = """
# This file is originally generated from Git information by running 'setup.py
# version'. Distribution tarballs contain a pre-generated copy of this file.

__version__ = '%s'
__date__ = '%s'
"""

def update_version_py():
    if not os.path.isdir(".git"):
        print "This does not appear to be a Git repository."
        return
    try:
        #p = subprocess.Popen(["git", "log","-1","--pretty=format:%h"],
        #                     stdout=subprocess.PIPE)
        p = subprocess.Popen(["git", "describe"],
                             stdout=subprocess.PIPE)
    except EnvironmentError:
        print "unable to run git, leaving mwapy/_version.py alone"
        return
    stdout = p.communicate()[0]
    if p.returncode != 0:
        print "unable to run git, leaving mwapy/_version.py alone"
        return
    # we use tags like "python-ecdsa-0.5", so strip the prefix
    #assert stdout.startswith("python-ecdsa-")
    #ver = stdout[len("python-ecdsa-"):].strip()
    ver=stdout.strip()

    try:
        p = subprocess.Popen(["git", "log","-1","--pretty=format:%ci"],
                             stdout=subprocess.PIPE)
    except EnvironmentError:
        print "unable to run git, leaving mwapy/_version.py alone"
        return
    stdout = p.communicate()[0]
    if p.returncode != 0:
        print "unable to run git, leaving mwapy/_version.py alone"
        return
    date=stdout
    
    f = open("mwapy/_version.py", "w")
    f.write(VERSION_PY % (ver,date))
    f.close()
    print "set mwapy/_version.py to '%s' with date '%s'" % (ver,date)

def get_version():
    try:
        f = open("mwapy/_version.py")
    except EnvironmentError:
        return None
    for line in f.readlines():
        mo = re.match("__version__ = '([^']+)'", line)
        if mo:
            ver = mo.group(1)
            return ver
    return None
def get_versiondate():
    try:
        f = open("mwapy/_version.py")
    except EnvironmentError:
        return None
    for line in f.readlines():
        mo = re.match("__date__ = '([^']+)'", line)
        if mo:
            date = mo.group(1)
            return date
    return None

class Version(Command):
    description = "update _version.py from Git repo"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        update_version_py()
        print "Version is now", get_version()

class sdist(_sdist):
    def run(self):
        update_version_py()
        # unless we update this, the sdist command will keep using the old
        # version
        self.distribution.metadata.version = get_version()
        return _sdist.run(self)




setup(
    name = "mwapy",
    #version = "0.0.2",
    version=get_version(),
    author = "D. Jacobs",
    author_email = "daniel.c.jacobs@asu.edu",
    description = ("Set of tools for using and developing the MWA."),
    license = "BSD",
    cmdclass={ "version": Version},
    keywords = "MWA radio",
    url = "http://mwa-lfd.haystack.mit.edu",
    py_modules = ['mwa_32T_pb','mwaconfig'],
    packages=packages,
    package_dir={'mwapy':'mwapy','':'configs'},
    scripts=glob('scripts/*')+['CONV2UVFITS/corr2uvfits'] + ['build_lfiles/build_lfiles'] + ['build_lfiles/read_mwac'],
    ext_modules=[
#    Extension('SLALIB',
#    glob('mwapy/CONV2UVFITS/SLALIB_C/*.o')
#    ),
#    Extension('CONV2UVFITS',
#        ['mwapy/CONV2UVFITS/corr2uvfits.c',
#        'mwapy/CONV2UVFITS/uvfits.c'],
#        libraries=['cfitsio','sla','m'],
#        library_dirs = ['mwapy/CONV2UVFITS/SLALIB_C'],
#        include_dirs = ['mwapy/CONV2UVFITS/SLALIB_C'],
#        )
#        extra_compile_args=[' -O -Wall -D_FILE_OFFSET_BITS=64 -L. '])
    Extension(name='mwapy.eorpy.igrf11_python',
              sources=['mwapy/eorpy/igrf11_python.f'],
              #f2py_options=['--f77flags="-ffixed-line-length-none"']
              )
    ],
    long_description=read('README'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
#    data_files=[('',['configs/mwa.conf'])],
    package_data={'mwapy.pb':['*.txt','*.fits'],
    'mwapy.catalog':['*.vot'],'mwapy':['../configs/mwa.conf','../configs/*.def','../configs/*.txt']})
