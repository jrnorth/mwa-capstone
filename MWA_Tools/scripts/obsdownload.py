#!/usr/bin/env python
import sys, os, time, socket, json
from optparse import OptionParser
import threading
import urllib2, urllib
import base64
import time

username = 'ngas'
password = base64.decodestring('bmdhcw==')
    
class PrintStatus():
    
    def __init__(self, numfiles):
        self.status = {}
        self.lock = threading.RLock()
        self.currentbytes = 0
        self.totalbytes = 0
        self.runtime = 0
        self.errors = []
        self.files = 0
        self.filesComplete = 0
        self.totalfiles = numfiles;

    
    def fileError(self, err):
        with self.lock:
            self.errors.append(err)
            print err
        
    def fileStarting(self, filename):
        with self.lock:
            print "%s [INFO] Downloading %s" % (time.strftime("%c"), filename)
            
    def fileComplete(self, filename):
        with self.lock:
            self.filesComplete = self.filesComplete + 1
            print "%s [INFO] %s complete [%d of %d]" % (time.strftime("%c"), filename, self.filesComplete, self.totalfiles)
            

def queryObs(obs, host, flagonly):
    #http://fe1.pawsey.ivec.org:7777/QUERY?query=files_like&like=1061316296%&format=json
    
    base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    
    url = 'http://%s/QUERY?' % host
    data = "query=files_like&like=" + str(obs) + "%&format=json"
    
    response = None
    try:
        # Send HTTP POST request
        request = urllib2.Request(url + data)
        request.add_header("Authorization", "Basic %s" % base64string)   
        
        response = urllib2.urlopen(request)
        
        resultbuffer = ''
        while True:
            result = response.read(2048)
            if result:
                resultbuffer = resultbuffer + result
            else:
                break

        filemap = {}
        files = json.loads(resultbuffer)['files_like']
                
        for f in files:
            # retrieve flag files only
            if flagonly:
                if 'flags.zip' in f['col3']:
                    filemap[f['col3']] = f['col6']
            # else add all the files: having a map removes diplicates
            else:
                filemap[f['col3']] = f['col6']
        
        return filemap
    
    finally:
        if response:
            response.close()

 

def checkFile(filename, size, dir):
    path = dir + filename
        
    # check the file exists
    if os.path.isfile(path) is True:
        #check the filesize matches
        filesize = os.stat(path).st_size

        if filesize == int(size):
            return True
        
    return False


def worker(url, size, filename, s, out, stat, bufsize):
    u = None
    f = None
    
    try:
        stat.fileStarting(filename)

        # open file URL
        request = urllib2.Request(url)
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)   
        
        u = urllib2.urlopen(request, timeout=1400)        
        u.fp.bufsize = bufsize
        
        # get file size
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        
        # open file for writing
        f = open(out + filename, 'wb')
        
        current = 0
        file_size_dl = 0
        block_sz = bufsize
        
        while file_size_dl < file_size:
            buffer = u.read(block_sz)
            if buffer:
                f.write(buffer)

                current = len(buffer)
                file_size_dl += current
                
            else:
                if file_size_dl != file_size:
                    raise Exception("size mismatch %s %s" % str(file_size), str(file_size_dl))
                
                break

        stat.fileComplete(filename)
        
    except urllib2.HTTPError as e:
        stat.fileError("%s [ERROR] %s %s" % (time.strftime("%c"), filename, str(e.read()) ))
    
    except urllib2.URLError as urlerror:
        if hasattr(urlerror, 'reason'):
            stat.fileError("%s [ERROR] %s %s" % (time.strftime("%c"), filename, str(urlerror.reason) ))
        else:
            stat.fileError("%s [ERROR] %s %s" % (time.strftime("%c"), filename, str(urlerror) ))
    
    except Exception as exp:
        stat.fileError("%s [ERROR] %s %s" % (time.strftime("%c"), filename, str(exp) ))
        
    finally:
        if u != None:
            u.close()
            
        if f != None:
            f.flush()
            f.close()
            
        s.release()
        


def main():
    stat = None
    
    try:
        parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
        parser.add_option("-o", action="store", dest="obs", help="Observation ID")
        parser.add_option("-k",  default='fe1.pawsey.ivec.org:7777', action="store", dest="ngashost", help="NGAS Server (default: fe1.pawsey.ivec.org:777)")
        parser.add_option("-f", default=False, action="store_true", dest="flagfile", help="Download only the flag file (default: False)")
        parser.add_option("-d", default= './', action="store", dest="out", help="Output directory (default: ./<Observation ID>")
        parser.add_option("-t", default='4', action="store", dest="td", help="Number of simultaneous downloads (default: 4)")
        
        # get system TCP buffer size
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bufsize = s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        s.close()
        
        (options, args) = parser.parse_args()
        
        if options.ngashost == None:
            print 'NGAS host not defined'
            sys.exit(-1)
            
        if options.obs == None:
            print 'Observation ID is empty'
            sys.exit(-1)
            
        numdownload = int(options.td)
        
        if numdownload <= 0 or numdownload > 6:
            print 'Number of simultaneous downloads must be > 0 and <= 6'
            sys.exit(-1)
        
        print '%s [INFO] Finding observation %s' % (time.strftime("%c"), options.obs,)


        fileresult = queryObs(options.obs, options.ngashost, options.flagfile)
        
        if len(fileresult) <= 0:
            print '%s [INFO] No files found for observation %s' % (time.strftime("%c"), options.obs,)
            sys.exit(1)
        
        print '%s [INFO] Found %s files' % (time.strftime("%c"), str(len(fileresult)),)
        
        if options.out == None or len(options.out) == 0:
            options.out = './'

        # check we have a forward slash before file
        if options.out[len(options.out)-1] != '/':
             options.out += '/'

        dir = options.out + options.obs + '/'
        if not os.path.exists(dir):
            os.makedirs(dir)
        
        stat = PrintStatus(len(fileresult))
        urls = []
        
        for key, value in fileresult.iteritems():
            url = "http://" + options.ngashost + "/RETRIEVE?file_id=" + key
            if checkFile(key, int(value), dir) is False:
                urls.append((url, value, key))
                #stat.update(url, r[2], 0, 0, 0, 0)    
            else:
                stat.fileComplete(key)

        s = threading.BoundedSemaphore(value=numdownload)        
        for u in urls:
            while(1):
                if s.acquire(blocking=False):
                    t = threading.Thread(target=worker, args=(u[0],u[1],u[2],s,dir,stat,int(bufsize)))
                    t.setDaemon(True)
                    t.start()
                    break
                else:
                    time.sleep(1)

        while (1):
            main_thread = threading.currentThread()
            #if the main thread and print thread are left then we must be done; else wait join
            if len(threading.enumerate()) == 1:
                break;
            
            for t in threading.enumerate():
                #if t is main_thread or t is status_thread:
                if t is main_thread:
                    continue
                
                t.join(1)
                if t.isAlive():
                    continue

        print "%s [INFO] File Transfer Complete." % (time.strftime("%c"))
        
        # check if we have errors
        if len(stat.errors) > 0:
            print "%s [INFO] File Transfer Error Summary:" % (time.strftime("%c"))
            for i in stat.errors:
                print i
                
            raise Exception()
        else:
            print "%s [INFO] File Transfer Success." % (time.strftime("%c"))
            
    except KeyboardInterrupt as k:
        raise k
    
    except Exception as e:
        raise e

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
        
    except KeyboardInterrupt as k:
        print 'Interrupted, shutting down'
        sys.exit(2)
    
    except Exception as e:
        print e
        sys.exit(3)