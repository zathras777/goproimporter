goproimporter
=============

GoPro Timelapse Import Script

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

