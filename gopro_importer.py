#! /usr/bin/env python

'''
  This script automates the importing of sequences of JPEG images taken
  using a GoPro Hero 2. The images are generated using a sensible filename
  but they are often spread across several different directories, so this
  script tries to make sense of them and extract them into a single
  directory with sequential file names to make creating the timelapse movie
  simpler.
  
  To use it needs the PIL library.
  
  Simple usage:
  
    ./gopro_importer.py --dest ~/destination --prefix hello /mounted/gopro

  This will look for timelapse sequences and give you the option to extract
  each in turn, storing the images it copies using the filenames
  
     /destination/hello_n/xxx.JPG
  
  where 'n' is the number of the timelapse and xxx is the 8 digit sequence
  number.

  NB Use at your own risk!
'''

import re
import os
import argparse
import Image

from datetime import datetime
from shutil import copyfile

DIR_re = re.compile("^([0-9]{3})GOPRO$")

def sizeof_fmt(num):
    for x in ['bytes','KB','MB','GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')

class TimelapseImage(object):
    FILE_re = re.compile("^G([0-9]{3})([0-9]{4}).JPG$")
    def __init__(self, fn, folder):
        if not os.path.exists(fn):
            return
        self.fn = fn
        self.folder = folder
        self.group = 0
        ck = self.FILE_re.match(os.path.basename(fn))
        if ck:
            self.group = int(ck.group(1))
            self.seq = int(ck.group(2))
            self.when = self.get_exif_time()
            self.size = os.path.getsize(fn)
            self.basefn, self.ext = os.path.splitext(os.path.basename(fn))
            
    def get_exif_time(self):
        img = Image.open(self.fn)
        if hasattr(img, '_getexif'):
            exifdata = img._getexif()
            return datetime.strptime(exifdata[0x9003], "%Y:%m:%d %H:%M:%S")

    def sortname(self):
        return u"%d_%03d_%s_%04d" % (self.group, self.folder,
                                      self.when.strftime("%Y%m%d%H%M%S"), 
                                      self.seq)

    def dup_fn(self, dirname):
        fn = "%s_%04d%s" % (self.when.strftime("%Y%m%d%H%M%S"), self.seq, self.ext)
        return os.path.join(dirname, fn)
        
class Timelapse(object):
    def __init__(self, number):
        self.images = []
        self.number = number
        self.first = None
        self.last = None
        self.size = 0
        
    def add_image(self, ti):
        if ti.group != self.number:
            return
        if len(self.images) == 0:
            self.first = ti.when
        self.images.append(ti)
        if self.last is None or self.last < ti.when:
            self.last = ti.when
        self.size += ti.size
        
    def sorted_images(self):
        return sorted(self.images, key=lambda x: x.sortname())

    def copy_files(self, basedir, prefix):
        newdir = os.path.join(basedir, "%s_%03d" % (prefix, self.number))
        if os.path.exists(newdir):
            print "WARNING: output directory already exists"
            x = 0
            while os.path.exists(newdir):
                newdir = os.path.join(basedir, "%s_%03d_%d" % (prefix, self.number, x))
                x += 1
            print "         using unique directory name: %s" % os.path.basename(newdir)
        os.makedirs(newdir)
        n = 1
        for ti in self.sorted_images():
            fn = os.path.join(newdir, "%08d%s" % (n, ti.ext))
            copyfile(ti.fn, fn)
            n += 1
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import timelapse images from GoPro')
    parser.add_argument('-d','--debug', action='store_true', 
                        help="Debug, don't copy anything")
    parser.add_argument('mountpoint', help='Location of mounted GoPro or SD Card')
    parser.add_argument('--prefix', action='store', default='GoPro', 
                        help='Prefix for created directories')
    parser.add_argument('--dest', action='store', 
                        default=os.path.dirname(__file__), 
                        help='Destination for created directories')
    args = parser.parse_args()
    
    if not os.path.exists(args.mountpoint):
        print "Mount point %s does not exist." % args.mountpoint
        sys.exit(0)
    dcim = os.path.join(args.mountpoint, 'DCIM')
    if not os.path.exists(dcim):
        print "No DCIM directory found on mountpoint %s" % args.mountpoint
        sys.exit(0)

    timelapses = {}
    
    print "Starting scan of %s" % dcim
    nfiles = 0
    for d in os.listdir(dcim):
        possdir = os.path.join(dcim, d)
        if not os.path.isdir(possdir):
            print "Skipping %s as not a directory" % possdir
            continue
        ck = DIR_re.match(d)
        if ck is None:
            print "Skipping %s as does not appear to be a GoPro directory" % possdir
            continue
        folder = ck.group(1)
        for f in os.listdir(possdir):
            nfiles += 1
            ti = TimelapseImage(os.path.join(possdir, f), folder)
            if ti.group == 0:
                # Not a timelapse sequence image
                continue
            if not timelapses.has_key(ti.group):
                timelapses[ti.group] = Timelapse(ti.group)
            timelapses[ti.group].add_image(ti)

    print "Scan completed. Total of %d files examined.\n" % nfiles
    for t in timelapses.itervalues():
        print "\n    Timelapse %d" % t.number
        print "        Started   %s" % t.first.strftime("%d %B %Y %H:%M:%S")
        print "        Finished  %s" % t.last.strftime("%d %B %Y %H:%M:%S")
        print "        %d images, %s disk space required" % (len(t.images), sizeof_fmt(t.size))
        resp = raw_input("\n        Process? (y/n) => ")
        if len(resp) and resp[0] in ['Y','y']:
            t.copy_files(args.dest, args.prefix)
            print "        Copied\n"
        else:
            print "        Skipped...\n"
                

