#!/usr/bin/env python
# sudo mount_nfs -P 192.168.0.2:/volume1/photo /Users/phillips321/nfsmount
# Author:       phillips321
# License:      CC BY-SA 3.0
# Use:          home use only, commercial use by permission only
# Released:     www.phillips321.co.uk
# Dependencies: PIL, libjpeg, libpng, dcraw, ffmpeg
# Supports:     jpg, bmp, png, tif
# Version:      5.0
# ChangeLog:
#       v5.0 - addition of PREVIEW thumbnail type; check for proper video conversion command
#       v4.0 - addition of autorate (thanks Markus Luisser)
#       v3.1 - filename fix (_ instead of :) and improvement of rendering (antialias and quality=90 - thanks to alkopedia)
#       v3.0 - Video support 
#       v2.1 - CR2 raw support
#       v2.0 - multithreaded
#       v1.0 - First release
# ToDo:
#       add more raw formats
#       add more movie formats

from PIL import Image, ImageChops, ImageFile
from io import StringIO
from multiprocessing import Pool
import os, errno, sys, time, subprocess, shlex

#########################################################################
# Settings
#########################################################################
NumOfThreads = os.cpu_count()                                                                                                                                                                                     # Number of threads
startTime = time.time()

imageExtensions = ['.jpg', '.png', '.jpeg', '.tif', '.bmp', '.cr2']  # possibly add other raw types?
videoExtensions = ['.mov', '.m4v', '.mp4', '.avi', '.mts']

xlName = "SYNOPHOTO_THUMB_XL.jpg";
xlSize = (1280, 1280)  # XtraLarge
lName = "SYNOPHOTO_THUMB_L.jpg";
lSize = (800, 800)  # Large
bName = "SYNOPHOTO_THUMB_B.jpg";
bSize = (640, 640)  # Big
mName = "SYNOPHOTO_THUMB_M.jpg";
mSize = (320, 320)  # Medium
sName = "SYNOPHOTO_THUMB_S.jpg";
sSize = (160, 160)  # Small
pName = "SYNOPHOTO_THUMB_PREVIEW.jpg";
pSize = (120, 160)  # Preview, keep ratio, pad with black

ImageFile.LOAD_TRUNCATED_IMAGES = True  # prevents Pillow's ImageFile from 'file truncated' problem


#########################################################################
# Images Class - converted to method executed on single file path
#########################################################################
def convertImage(imagePath):
    imageDir, imageName = os.path.split(imagePath)
    thumbDir = os.path.join(imageDir, "@eaDir", imageName)
    print("\t Now working on {}".format(imagePath))
    if not os.path.isfile(os.path.join(thumbDir, xlName)):
        if not os.path.isdir(thumbDir):
            try:
                os.makedirs(thumbDir)
            except OSError:
                return False

            # Following if statements converts raw images using dcraw first
            if os.path.splitext(imagePath)[1].lower() == ".cr2":
                dcrawcmd = "dcraw -c -b 8 -q 0 -w -H 5 '%s'" % imagePath
                dcraw_proc = subprocess.Popen(shlex.split(dcrawcmd), stdout=subprocess.PIPE)
                raw = StringIO(dcraw_proc.communicate()[0])
                image = Image.open(raw)
            else:
                image = Image.open(imagePath)

            ###### Check image orientation and rotate if necessary
            ## code adapted from: http://www.lifl.fr/~riquetd/auto-rotating-pictures-using-pil.html
            exif = image._getexif()

            if not exif:
                print("\t File {} had no EXIF data.".format(imagePath))
                return False

            orientation_key = 274  # cf ExifTags
            if orientation_key in exif:
                orientation = exif[orientation_key]

                rotate_values = {
                    3: 180,
                    6: 270,
                    8: 90
                }

                if orientation in rotate_values:
                    image = image.rotate(rotate_values[orientation])

            # try:
            image.thumbnail(xlSize, Image.ANTIALIAS)
            image.save(os.path.join(thumbDir, xlName), quality=90)
            image.thumbnail(lSize, Image.ANTIALIAS)
            image.save(os.path.join(thumbDir, lName), quality=90)
            image.thumbnail(bSize, Image.ANTIALIAS)
            image.save(os.path.join(thumbDir, bName), quality=90)
            image.thumbnail(mSize, Image.ANTIALIAS)
            image.save(os.path.join(thumbDir, mName), quality=90)
            image.thumbnail(sSize, Image.ANTIALIAS)
            image.save(os.path.join(thumbDir, sName), quality=90)
            image.thumbnail(pSize, Image.ANTIALIAS)
            # pad out image
            image_size = image.size
            preview_img = image.crop((0, 0, pSize[0], pSize[1]))
            offset_x = max((pSize[0] - image_size[0]) / 2, 0)
            offset_y = max((pSize[1] - image_size[1]) / 2, 0)
            preview_img = ImageChops.offset(preview_img, int(offset_x), int(offset_y))
            preview_img.save(os.path.join(thumbDir, pName), quality=90)
            # except OSError as e:
            #    print("Processing file: {} failed with exception: {}".format(imageName, e))
            #    continue


def is_tool(name):
    try:
        devnull = open(os.devnull)
        subprocess.Popen([name], stdout=devnull, stderr=devnull).communicate()
    except OSError as e:
        if e.errno == errno.ENOENT:
            return False
    return True


#########################################################################
# Video Class - converted to method executed on single file path
#########################################################################
def convertVideo(videoPath):
    videoDir, videoName = os.path.split(videoPath)
    thumbDir = os.path.join(videoDir, "@eaDir", videoName)
    # if not os.path.isfile(os.path.join(thumbDir, xlName)):
    if not os.path.isfile(os.path.join(thumbDir,"SYNOPHOTO:FILM.flv")):
        print("\t Now working on {}".format(videoPath))
        if not os.path.isdir(thumbDir):
            try:
                os.makedirs(thumbDir)
            except OSError:
                return False

        # Check video conversion command and convert video to flv
        if is_tool("ffmpeg"):
            ffmpegcmd = "ffmpeg -loglevel panic -i '%s' -y -ar 44100 -r 12 -ac 2 -f flv -qscale 5 -s 320x180 -aspect 320:180 '%s/SYNOPHOTO:FILM.flv'" % (
                videoPath, thumbDir)  # ffmpeg replaced by avconv on ubuntu
        elif is_tool("avconv"):
            ffmpegcmd = "avconv -loglevel panic -i '%s' -y -ar 44100 -r 12 -ac 2 -f flv -qscale 5 -s 320x180 -aspect 320:180 '%s/SYNOPHOTO:FILM.flv'" % (
                videoPath, thumbDir)
        else:
            print("\t FLV conversion for {} not done: ffmpeg/avconv not available?!?".format(videoName))
            return False

        ffmpegproc = subprocess.Popen(shlex.split(ffmpegcmd), stdout=subprocess.PIPE)
        ffmpegproc.communicate()[0]

        # Create video thumbs
        tempThumb = os.path.join("/tmp", os.path.splitext(videoName)[0] + ".jpg")
        if is_tool("ffmpeg"):
            ffmpegcmdThumb = "ffmpeg -loglevel panic -i '%s' -y -an -ss 00:00:03 -an -r 1 -vframes 1 '%s'" % (
                videoPath, tempThumb)  # ffmpeg replaced by avconv on ubuntu
        elif is_tool("avconv"):
            ffmpegcmdThumb = "avconv -loglevel panic -i '%s' -y -an -ss 00:00:03 -an -r 1 -vframes 1 '%s'" % (
                videoPath, tempThumb)
        else:
            print("\t Thumbnail for {} not rnedered: ffmpeg/avconv not available?!?".format(videoName))
            return False
        try:
            ffmpegThumbproc = subprocess.Popen(shlex.split(ffmpegcmdThumb), stdout=subprocess.PIPE)
            ffmpegThumbproc.communicate()[0]
            image = Image.open(tempThumb)
            image.thumbnail(xlSize)
            image.save(os.path.join(thumbDir, xlName))
            image.thumbnail(mSize)
            image.save(os.path.join(thumbDir, mName))
        except OSError as e:
            print("\t Error encountered: {}".format(e))
            return False
    else:
        print("{} already converted".format(videoName))

#########################################################################
# Main
#########################################################################
def main():
    if len(sys.argv) == 1:
        print("Usage: {} directory".format(sys.argv[0]))
        sys.exit(0)

    # Finds all images of type in extensions array
    rootdir = sys.argv[1]
    imageList = []
    print("[+] Looking for images and populating queue (This might take a while...)")
    for path, subFolders, files in os.walk(rootdir, topdown=True):
        subFolders[:] = [d for d in subFolders if d != '@eaDir']
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if any(x in ext for x in imageExtensions):  # check if extensions matches ext
                if file != ".DS_Store" and file != ".apdisk" and file != "Thumbs.db":  # maybe remove
                    imageList.append(os.path.join(path, file))

    imageList.sort()

    print("[+] We have found {} images in search directory".format(len(imageList)))
    input("\tPress Enter to continue or Ctrl-C to quit")

    # spawn a pool of threads
    imgPool = Pool(os.cpu_count())
    imgPool.map(convertImage, imageList)
    imgPool.close()
    imgPool.join()

    # Finds all videos of type in extensions array
    videoList = []

    print("[+] Looking for videos and populating queue (This might take a while...)")
    for path, subFolders, files in os.walk(rootdir, topdown=True):
        subFolders[:] = [d for d in subFolders if d != '@eaDir']
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if any(x in ext for x in videoExtensions):  # check if extensions matches ext
                if file != ".DS_Store" and file != ".apdisk" and file != "Thumbs.db":  # maybe remove?
                    videoList.append(os.path.join(path, file))

    videoList.sort()
    print("[+] We have found {} videos in search directory".format(len(videoList)))
    input("\tPress Enter to continue or Ctrl-C to quit")

    # spawn a pool of threads
    videoPool = Pool(os.cpu_count())
    videoPool.map(convertVideo, videoList)
    videoPool.close()
    videoPool.join()

    endTime = time.time()
    print("[+] Time to complete {} (seconds)".format(endTime - startTime))
    sys.exit(0)


if __name__ == "__main__":
    main()
