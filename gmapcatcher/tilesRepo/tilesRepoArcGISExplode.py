# -*- coding: utf-8 -*-
## @package gmapcatcher.tilesRepo.tilesRepoArcGISExplode
# This modul provides filebased tile repository functions
#
# Usage:
#
# - constructor requires MapServ instance, because method
#  'get_tile_from_coord' is provided in the MapServ
#
# tilesRepoArcGISExplode exports tiles in ArcGIS cache format
# Copyright (C) 2015  Marco Draeger
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import os
import gmapcatcher.lrucache as lrucache
import gmapcatcher.fileUtils as fileUtils
import gmapcatcher.widgets.mapPixbuf as mapPixbuf

from threading import Lock
from gmapcatcher.mapConst import *
from tilesRepo import TilesRepository
from tilesRepoSQLite3 import tileNotInRepository


class TilesRepositoryArcGISExplode(TilesRepository):

    def __init__(self, MapServ_inst, conf):
        TilesRepository.__init__(self, MapServ_inst, conf)
        self.configpath = conf.init_path
        self.tile_cache = lrucache.LRUCache(1000)
        self.mapServ_inst = MapServ_inst
        self.lock = Lock()
        self.missingPixbuf = mapPixbuf.missing()

    def finish(self):
        # last command in finish
        TilesRepository.finish(self)

    ## Sets new repository path to be used for storing tiles
    def set_repository_path(self, conf):
        self.configpath = conf.init_path

    ## check if we have locally downloaded tile
    def is_tile_in_local_repos(self, coord, layer):
        path = self.coord_to_path(coord, layer)
        return  os.path.isfile(path)

    ## Returns the PixBuf of the tile
    #  Uses a cache to optimise HDD read access
    def load_pixbuf(self, coord, layer, force_update):
        filename = self.coord_to_path(coord, layer)
        if not force_update and (filename in self.tile_cache):
            pixbuf = self.tile_cache[filename]
        else:
            if os.path.isfile(filename):
                try:
                    pixbuf = mapPixbuf.image_data_fs(filename)
                    self.tile_cache[filename] = pixbuf
                except Exception:
                    pixbuf = self.missingPixbuf
                    print "File corrupted: %s" % filename
                    fileUtils.del_file(filename)
            else:
                pixbuf = self.missingPixbuf
        return pixbuf

    ## Get the png file for the given location
    #  Returns true if the file is successfully retrieved
    def get_png_file(self, coord, layer,
                        online, force_update, conf):
        filename = self.coord_to_path(coord, layer)
        # remove tile only when online
        remove_tile = False
        if (force_update and online):
            remove_tile = fileUtils.is_old(filename, conf.force_update_days)

        if os.path.isfile(filename) and not remove_tile:
            return True
        if not online:
            return False

        try:
            data = self.mapServ_inst.get_tile_from_coord(
                        coord, layer, conf
                    )
            self.coord_to_path_checkdirs(coord, layer)
            # Remove the old tile only after getting the new data
            if remove_tile:
                fileUtils.delete_old(filename, conf.force_update_days)
            file = open(filename, 'wb')
            file.write(data)
            file.close()

            return True
        except KeyboardInterrupt:
            raise
        except Exception, excInst:
            print excInst
        return False

    def get_plain_tile(self, coord, layer):
        if not self.is_tile_in_local_repos(coord, layer):
            raise tileNotInRepository(str((coord, layer)))

        filename = self.coord_to_path(coord, layer)
        thefile = open(filename, 'rb')
        ret = thefile.read()
        thefile.close()
        return ret

    def store_plain_tile(self, coord, layer, tiledata):
        filename = self.coord_to_path_checkdirs(coord, layer)
        file = open(filename, 'wb')
        file.write(tiledata)
        file.close()

    ## Return the absolute path to a tile
    #  only check path
    #  tile_coord = (zoom_level, tile_Y, tile_X)
    #  sample of the Naming convention:
    #  \.googlemaps\ArcGIS\_allLayers\L00\R0000002\C0000001.png
    #  We only have 2 levels for one axis
    # private
    def coord_to_path(self, tile_coord, layer):
        column = 'C' + ("%08x" % tile_coord[0]).lower()
        row    = 'R' + ("%08x" % tile_coord[1]).lower()
        zoom   = 'L' + ("%02d" % (MAP_MAX_ZOOM_LEVEL - tile_coord[2]))
        return os.path.join(
                            self.configpath,
                            "ArcGIS_" + LAYER_DIRS[layer],
                            "_alllayers",
                            zoom, row, column + ".png"
                           )

    ## create path if doesn't exists
    #  tile_coord = (zoom_level, tile_Y, tile_X)
    #  sample of the Naming convention:
    #  \.googlemaps\ArcGIS\_allLayers\L00\R0000002\C0000001.png
    #  We only have 2 levels for one axis
    # private
    def coord_to_path_checkdirs(self, tile_coord, layer):
        column = 'C' + ("%08x" % tile_coord[0]).lower()
        row    = 'R' + ("%08x" % tile_coord[1]).lower()
        zoom   = 'L' + ("%02d" % (MAP_MAX_ZOOM_LEVEL - tile_coord[2]))
        self.lock.acquire()
        path = os.path.join(self.configpath, "ArcGIS_" + LAYER_DIRS[layer])
        path = fileUtils.check_dir(path)
        path = fileUtils.check_dir(path, "_alllayers")
        path = fileUtils.check_dir(path, zoom)
        path = fileUtils.check_dir(path, row)
        self.lock.release()
        return os.path.join(path, column + '.png')
