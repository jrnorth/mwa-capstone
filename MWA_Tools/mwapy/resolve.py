import urllib2, urllib, base64
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.etree import ElementTree
import re
from datetime import datetime
from urlparse import urlparse

class NGASException(Exception):
    
    MALFORMED_URI = 1
    FILE_NOT_FOUND = 2
    NOT_ONLINE = 3
    GENERAL_ERROR = 4
    UNAUTHORISED = 5
    
    def __init__(self, errorcode, value):
        self.errorcode = errorcode
        self.value = value
        
    def __str__(self):
        return repr(self.value)
    
''' 
Resolves MWA NGAS URI into a list of downloadable NGAS URLs

params: 
    resolvehost: host and port of resolver <host:port>
    uri: MWA NGAS URI Example: http://mwangas/RETRIEVE?file_id=12345_20120504054724_32_02.vis

return:
    NGAS URL
'''

def resolveURI(resolvehost, uri):
    
    sock = None
    data = {}
    data['uri'] = uri

    url_values = urllib.urlencode(data)
    full_url = "http://" + resolvehost + "/ngas/RESOLVE/?" + url_values

    try:
        sock =  urllib2.urlopen(full_url)
        buff = None
        block_sz = 87380
        while True:
            buffer = sock.read(block_sz)
            if not buffer:
                break
        
            if (buff == None):
                buff = buffer
            else:
                buff = buff + buffer

        ele = ElementTree.XML(buff)
        res = ele.find('Result')
        if res.text == 'OK':
            urlsEle = ele.find('URL')
            
            return urlsEle.text
        else:
            raise NGASException(ele.find('ErrorCode').text, ele.find('ErrorDescription').text)
        
    finally:
        if sock:
            sock.close()

'''
Parse out obs id, time, host and part from an MWA correlator file
Fileid format:
    <id>_<time>_<host>_<partnumber>.vis
Note:
    <time> is %Y%m%d%H%M%S
'''
def parseFileID(fileid):
    
    sp = re.split(r'([_])', fileid)

    id = sp[0]
    time = datetime.strptime(sp[2], '%Y%m%d%H%M%S')
    host = sp[4].replace('.fits', '')
        
    part = 0
    
    try:
        part = int(re.split(r'([.])', sp[6])[0])
        
    except Exception, e:
        pass
    
    return id, time, host, part

'''
Parse fileID out of URI 
'''
def parseURI(uri):
        #file = re.split(r'([=])', uri)
        file = re.split(r'file_id=', uri)
        return file[1]
    

'''
Resolves an MWA NGAS URI and downloads the first contactable NGAS URL. 
Creates and downloads the NGAS file defined in the URI to the local directory. 

params: 
    resolvehost: host and port of resolver <host:port>
    uri: MWA NGAS URI Example: http://mwangas/RETRIEVE?file_id=12345_20120504054724_32_02.vis
    out: output directory
'''
def downloadURI(resolvehost, uri, username, password, out = './'):
    # resolve URI to URL
    __download( resolveURI(resolvehost, uri), username, password, out)
    
'''
Download NGAS File

params:
    url: NGAS URL
    out: output directory
    
returns filename on success
'''
def downloadURL(url, username, password, out='./'):
    # download url directly: usually a product from parseURI
    return __download(url, username, password, out)


def __download(url, username, password, out):

    # extract filename
    file_name = parseURI(url)
    
    try:
        request = urllib2.Request(url)
        
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)   
        
        # open file URL
        u = urllib2.urlopen(request, timeout = 1800)
        
        # get file size
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
    
        print "Downloading: %s Bytes: %s" % (file_name, file_size)
        
        file_size_dl = 0
        block_sz = 87380
        
        try:
            if out == None or len(out) == 0:
                out = './'
            
            # check we have a forward slash before file
            if out[len(out)-1] != '/':
                 out += '/'
                 
            f = open(out + file_name, 'wb')
                
            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break
            
                file_size_dl += len(buffer)
                f.write(buffer)
                status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
                status = status + chr(8)*(len(status)+1)
                print status,
            
            return file_name
            
        finally:
            if f:
                f.close()
    finally:
        if u:
            u.close()