#!/usr/bin/env python
import sys, os, time, socket
from mwapy.resolve import *
from optparse import OptionParser
import psycopg2
import threading
import urllib2, urllib
from sys import stdout
from Queue import Queue, Empty
import mwaconfig
import base64

class PrintStatus():
    
    def __init__(self, stdscr):
        self.screen = stdscr
        self.status = {}
        self.lock = threading.RLock()
        self.currentbytes = 0
        self.totalbytes = 0
        self.runtime = 0
        self.errors = []
        self.files = 0
        self.filesComplete = 0
        self.diskbyteswritten = 0
        self.totaldiskbytes = 0
    
    def updateDisk(self, byteswritten):
        with self.lock:
            self.diskbyteswritten += byteswritten
            self.totaldiskbytes += byteswritten
    
    def update(self, url, file, size, downloaded, percent, current):
        with self.lock:
            self.status[url] = (file, size, downloaded, percent)
            self.files = len(self.status)
            self.currentbytes += current 
            self.totalbytes += current
    
    def error(self, err):
        with self.lock:
            self.errors.append(err)
            
    def filecomplete(self):
        with self.lock:
            self.filesComplete = self.filesComplete + 1
            
    def display(self):
        bytes = 0
        self.runtime += 1
        totalDownload = 0
        
        with self.lock:
            mbits =  '%3.2f' % (8*self.currentbytes/1024./1024.)
            mbytes =  '%3.2f' % (self.currentbytes/1024./1024.)
            diskbytes =  '%3.2f' % (self.diskbyteswritten/1024./1024.)
            self.currentbytes = 0
            self.diskbyteswritten = 0
            
            print
            print 'Running time: %s sec\n' % str(self.runtime),
            print 'Data rate: %s MB/s (%s Mb/s)\n' % (str(mbytes), str(mbits)),
            #print 'Disk rate: %s MB/s\n' % str(diskbytes),
    
            for i in self.status.items():
                totalDownload = totalDownload + int(i[1][2])
            
            totalDownload =  '%3.2f' % (totalDownload/1024./1024./1024.)
            print 'Total Downloaded: %s GB\n' % (str(totalDownload)),
            print 'Files Complete: %s of %s\n' % (str(self.filesComplete), str(self.files)),

        stdout.flush()

                
def status(stat):
    while (1):
        stat.display()
        time.sleep(1)
        

def _fileWriteThread(f, file_size, buffq, stat):   

    file_size_dl = 0

    while True:
        try:
            buffer = buffq.get(timeout = 0.5)
            f.write(buffer)
            bufflen = len(buffer)
            file_size_dl += bufflen
            stat.updateDisk(bufflen)
        except Empty as e:
            if (file_size_dl == file_size):
                break
            else:
                continue
        except Exception as a:
            print str(a)
            exit(-1)

def checkFile(filename, size, dir):
    path = dir + filename
        
    # check the file exists
    if os.path.isfile(path) is True:
        #check the filesize matches
        filesize = os.stat(path).st_size
        if filesize == size:
            return True
        
    return False

def worker(url, size, filename, s, out, stat, bufsize):
    u = None
    f = None
    #writethrd = None
    
    try:
        if out == None or len(out) == 0:
            out = './'
        
        # check we have a forward slash before file
        if out[len(out)-1] != '/':
             out += '/'
        
        # don't download file if it already exists and its the same size
        if checkFile(filename, size, out) is True:
            return
        
        current = 0
        
        # extract filename
        file_name = parseURI(url)
        # open file URL
        request = urllib2.Request(url)
        username = mwaconfig.mandc.ngasuser
        password = base64.decodestring(mwaconfig.mandc.ngaspass)
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)   
        u = urllib2.urlopen(request, timeout = 1200)
        
        u.fp.bufsize = bufsize
        
        # get file size
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        
        file_size_dl = 0
        block_sz = bufsize
             
        f = open(out + file_name, 'wb')
        
        #buffq = Queue()
        
        #write_args = (f, file_size, buffq, stat)
        #writethrd = threading.Thread(None, _fileWriteThread, "writer", write_args)
        #writethrd.setDaemon(True)
        #writethrd.start()
        
        while file_size_dl < file_size:
            buffer = u.read(block_sz)
            if buffer:
                current = len(buffer)
                file_size_dl += current
                
                f.write(buffer)
                #buffq.put(buffer)
                
                percent = '%3.2f%%' % (file_size_dl * 100. / file_size)
                stat.update(url, file_name, file_size, file_size_dl, percent, current)
            else:
                if file_size_dl != file_size:
                    stat.error("Size mismatch: %s, Size: %s, Downloaded: %s" % (file_name, str(file_size), str(file_size_dl)))
                
                break

    except urllib2.HTTPError as e:
        stat.error(file_name + " with err " + str(e.code))
        
    except Exception as exp:
        stat.error(file_name + " with err " + str(exp))
    finally:
        stat.filecomplete()
        
        #if (writethrd != None):
        #    writethrd.join()
        
        if u != None:
            u.close()
        if f != None:
            f.flush()
            f.close()
            
        s.release()
        
    

def main():
    
    conn = None
    stat = None
    stdscr = None
    
    try:
        parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")
        parser.add_option("-r", default=mwaconfig.mandc.dbhost, action="store", dest="host_port", help="NGAS resolver host:port")
        parser.add_option("-s", default=mwaconfig.mandc.dbhost, action="store", dest="dbhost", help="MWA database host")
        parser.add_option("-k", action="store", dest="ngashost", help="NGAS Download Host (bypass resolver)")
        parser.add_option("-p", default='5432', action="store", dest="dbport", help="MWA database port (default: 5432)")
        parser.add_option("-o", action="store", dest="obs", help="Observation ID")
        parser.add_option("-f", default=False, action="store_true", dest="flagfile", help="Download only the flag file (default: False)")
        parser.add_option("-d", action="store", dest="out", help="Output directory (default: ./<Observation ID>")
        parser.add_option("-t", default='4', action="store", dest="td", help="Number of simultaneous downloads (default: 4)")
        
        # get system TCP buffer size
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bufsize = s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        s.close()
        
        (options, args) = parser.parse_args()
        
        if options.host_port == None:
            print 'host:port is empty'
            sys.exit(-1)
            
        if options.obs == None:
            print 'Observation ID is empty'
            sys.exit(-1)
            
        if int(options.td) < 0:
            print 'Number of simultaneous downloads must be > 0\n'
            sys.exit(-1)
        
        print 'Finding observation %s' % (options.obs,)

        conn = psycopg2.connect(database=mwaconfig.mandc.dbname, user=mwaconfig.mandc.dbuser, password=base64.decodestring(mwaconfig.mandc.dbpass), host=options.dbhost, port=options.dbport)
        cur = conn.cursor()
        
        if options.flagfile is False:
            cur.execute('select site_path, size, filename from data_files where observation_num = %s and (filetype = 8 or filetype = 10)', [options.obs,])
        else:
            cur.execute('select site_path, size, filename from data_files where observation_num = %s and filetype = 10', [options.obs,])
        
        rows = cur.fetchall()
        
        if cur.rowcount <= 0:
            print 'No files found for observaiton %s' % (options.obs,)
            sys.exit(-1)
        
        urls = []
        
        for r in rows:
           
            print 'Resolving URI %s' % (r[0],)
        
            if options.ngashost is not None:
                url = "http://" + options.ngashost + "/RETRIEVE?file_id=" + r[2]
            else:
                try:
                    url = resolveURI(options.host_port, r[0])
                except Exception as n:
                    print n
                    continue
            
            print 'Resolved to %s, %s' % (url, r[1])
            
            urls.append((url, r[1], r[2]))

        conn.close()
        
        if options.out == None or len(options.out) == 0:
            options.out = './'

        # check we have a forward slash before file
        if options.out[len(options.out)-1] != '/':
             options.out += '/'

        dir = options.out + options.obs
        if not os.path.exists(dir):
            os.makedirs(dir)

        s = threading.Semaphore(int(options.td))
        stat = PrintStatus(stdscr)
        
        for u in urls:
            stat.update(u[0], parseURI(u[0]), '0', '0', '0', 0)
        
        status_thread = threading.Thread(target=status, args=(stat,))
        status_thread.setDaemon(True)
        status_thread.start()
        
        for u in urls:
            while(1):
                if s.acquire(blocking=False):
                    break
                else:
                    time.sleep(1)  
            
            t = threading.Thread(target=worker, args=(u[0],u[1],u[2],s,dir,stat,int(bufsize)))
            t.setDaemon(True)
            t.start()

        while (1):
            main_thread = threading.currentThread()
            #if the main thread and print thread are left then we must be done; else wait join
            if len(threading.enumerate()) == 2:
                break;
            
            for t in threading.enumerate():
                if t is main_thread or t is status_thread:
                    continue
                
                t.join(1)
                if t.isAlive():
                    continue

        if stat:
            print
            print 'Transfer Summary:'
            print 'Total downloaded: %d MB' % (stat.totalbytes/1024/1024,)
            print 'Total run time: %d seconds' % (stat.runtime,)
            print 'Avg data rate: %3.2f MB/s' % ((stat.totalbytes/stat.runtime)/1024/1024)
            #print 'Avg disk rate: %3.2f MB/s' % ((stat.totaldiskbytes/stat.runtime)/1024/1024)
            
        # check if we have errors
        if len(stat.errors) > 0:
            print
            print "Errors:"
            for i in stat.errors:
                print i
                
            raise Exception("File transfer errors!")
                    
    except KeyboardInterrupt as k:
        raise k
    
    except Exception as e:
        raise e
    
    finally:
        if conn:
            conn.close()
    
if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt as k:
        print 'Interrupted, shutting down'
        sys.exit(-1)
    
    except Exception as e:
        print e
        sys.exit(-1)
    
    
