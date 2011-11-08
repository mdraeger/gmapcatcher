#!/usr/bin/env python
# -*- coding: utf-8 -*-

## @package download
# Downloader tool without GUI

import sys
import gmapcatcher.mapConf as mapConf

from lxml import etree

from gmapcatcher.mapUtils import *
from gmapcatcher.mapArgs import MapArgs
from gmapcatcher.mapServices import MapServ
from gmapcatcher.mapDownloader import MapDownloader

mConf = mapConf.MapConf()
ctx_map = MapServ(mConf.init_path, mConf.repository_type)
downloader = None

def dl_callback(*args, **kwargs):
    if not args[0]:
        sys.stdout.write('\b=*')    

def download(lat, lng, lat_range, lng_range, max_zl, min_zl, layer):
    for zl in range(maz_zl, min_zl - 1, -1):
        sys.stdout.write("\nDownloading zl %d \t" % zl)
        downloader.query_region_around_location(
            lat, lng,
            lat_range*2, lng_range*2, zl,
            layer, dl_callback,
            conf=mConf
        )
        downloader.wait_all()

def download_coordpath(gpxfile, max_zl, min_zl, layer, arround=2):
    coords = load_gpx_coords(gpxfile)
    for zl in range(max_zl, min_zl - 1, -1):
        sys.stdout.write("\nDownloading zl %d \t" % zl)
        downloader.query_coordpath(coords, zl, arround, layer, dl_callback, conf=mConf) 
        downloader.wait_all()

def load_gpx_coords(gpxfile):
    tree = etree.parse(gpxfile)
    root = tree.getroot()
    xmlns = root.nsmap[None]

    coords = []
    for track in root.iter('{%s}trk' % xmlns):
        print 'Track found.'
        for pt in track.iter('{%s}trkpt' % xmlns):
            coords.append((float(pt.get('lat')), float(pt.get('lon'))))
    return coords

if __name__ == "__main__":
    args = MapArgs(sys.argv)

    if (args.location is None) and (args.gpx is None) and ((args.lat is None) or (args.lng is None)):
        args.print_help()
        sys.exit(0)

    print "location = %s" % args.location
    if ((args.lat is None) or (args.lng is None)) and (args.gpx is None):
        locations = ctx_map.get_locations()
        if (not args.location in locations.keys()):
            args.location = ctx_map.search_location(args.location)
            if (args.location[:6] == "error="):
                print args.location[6:]
                sys.exit(0)

        coord = ctx_map.get_locations()[args.location]
        args.lat = coord[0]
        args.lng = coord[1]

    if args.width > 0:
        args.lng_range = km_to_lon(args.width, args.lat)
    if args.height > 0:
        args.lat_range = km_to_lat(args.height)

    if (args.location is None):
        args.location = "somewhere"

    if args.gpx is None:
        print "Download %s (%f, %f), range (%f, %f), zoom level: %d to %d" % \
                (args.location, args.lat, args.lng,
                 args.lat_range, args.lng_range,
                 args.max_zl, args.min_zl)
    else:
        print "Download path in %s, zoom level: %d to %d" % \
                (args.gpx, args.max_zl, args.min_zl)

    downloader = MapDownloader(ctx_map, args.nr_threads)
    try:
        if args.gpx != None:
            download_coordpath(args.gpx, args.max_zl, args.min_zl, args.layer, arround=3)
        else:
            download(args.lat, args.lng, args.lat_range, args.lng_range,
                     args.max_zl, args.min_zl, args.layer)
    finally:
        print "\nDownload Complete!"
        downloader.stop_all()


