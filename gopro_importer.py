#! /usr/bin/env python

import re
import os
import argparse
import sys
from PIL import Image
import math

from datetime import datetime
from shutil import copyfile


if sys.version[0]=="3":
    raw_input=input


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
        self.seq = 0
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

    def copy_files(self, basedir, prefix, seq):
        self.seq = seq
        newdir = os.path.join(basedir, "%s_%03d" % (prefix, seq))
        if os.path.exists(newdir):
            while os.path.exists(newdir):
                self.seq += 1
                newdir = os.path.join(basedir, "%s_%03d" % (prefix, self.seq))
        os.makedirs(newdir)
        n = 1
        for ti in self.sorted_images():
            fn = os.path.join(newdir, "%08d%s" % (n, ti.ext))
            copyfile(ti.fn, fn)
            self.update_progress(n)
            n += 1
        print("\r\n\n        {} files copied to {}\n".format(n, newdir))
        
    def update_progress(self, progress):
        n = (float(progress) / len(self.images)) * 100
        bar = "#" * int(math.floor(n/2))
        sys.stdout.write('\r        Progress: [{:<50s}] {:.02f}%'.format(bar, n))
        sys.stdout.flush()

def read_sequence(thedir):
    if not os.path.exists(os.path.join(thedir, '.goproimport')):
        return 0
    with open(os.path.join(thedir, '.goproimport')) as fh:
        return int(fh.read())


def write_sequence(thedir, val):
    with open(os.path.join(thedir, '.goproimport'), 'w') as fh:
        fh.write("%d" % val)


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
        print("Mount point {} does not exist.".format(args.mountpoint))
        sys.exit(0)
    dcim = os.path.join(args.mountpoint, 'DCIM')
    if not os.path.exists(dcim):
        print("No DCIM directory found on mountpoint %s".format(args.mountpoint))
        sys.exit(0)

    timelapses = {}
    seq = read_sequence(args.dest)
    imported = 0

    print("Starting scan of {}".format(dcim))
    nfiles = 0
    for d in os.listdir(dcim):
        possdir = os.path.join(dcim, d)
        if not os.path.isdir(possdir):
            print("Skipped {} as not a directory".format(possdir))
            continue
        ck = DIR_re.match(d)
        if ck is None:
            print("Skipping {} as does not appear to be a GoPro directory".format(possdir))
            continue
        folder = int(ck.group(1))
        for f in os.listdir(possdir):
            nfiles += 1
            ti = TimelapseImage(os.path.join(possdir, f), folder)
            if ti.group == 0:
                # Not a timelapse sequence image
                continue
            if ti.group not in timelapses:
                timelapses[ti.group] = Timelapse(ti.group)
            timelapses[ti.group].add_image(ti)

    print("Scan completed. Total of {:,} files examined.".format(nfiles))
    for k in timelapses:
        t = timelapses[k]
        print("\n    Timelapse {}".format(t.number))
        print("        Started   {}".format(t.first.strftime("%d %B %Y %H:%M:%S")))
        print("        Finished  {}".format(t.last.strftime("%d %B %Y %H:%M:%S")))
        print("        {} images, {} disk space required".format(len(t.images), sizeof_fmt(t.size)))
        resp = raw_input("\n        Process? (y/n) => ")
        if len(resp) and resp[0] in ['Y','y']:
            t.copy_files(args.dest, args.prefix, seq)
            imported += 1
            seq = t.seq
        else:
            if len(resp) == 0:
                print("n")
            print("        Skipped...\n")

    if imported > 0:
        write_sequence(args.dest, seq)

