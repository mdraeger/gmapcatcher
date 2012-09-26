# -*- coding: utf-8 -*-
## @package gmapcatcher.widgets.trackWindow
# Widget that allows track control

import pygtk
pygtk.require('2.0')
import gtk

from customMsgBox import error_msg_non_blocking
from mapUtils import openGPX, saveGPX


class trackWindow(gtk.Window):
    def __init__(self, mapsObj):
        gtk.Window.__init__(self)
        self.mapsObj = mapsObj
        self.cb_tracks = list()
        vbox = gtk.VBox(False)
        vbox.pack_start(self._createTrackCB(mapsObj))
        vbox.pack_start(self._createButtons())
        self.set_title("GMapCatcher track control")
        self.set_border_width(10)
        self.add(vbox)
        self.show_all()
        self.update_widgets()

    def _createTrackCB(self, mapsObj):
        frame = gtk.Frame()
        frame.set_border_width(10)
        vbox = gtk.VBox(False, 10)
        self.no_tracks = gtk.Label()
        self.no_tracks.set_text("<b><span foreground=\"red\">No Tracks Found!</span></b>")
        self.no_tracks.set_use_markup(True)
        vbox.pack_start(self.no_tracks)
        alignment = gtk.Alignment(0.5, 0.5, 0, 0)
        self.track_vbox = gtk.VBox(False)
        for i in range(len(mapsObj.tracks)):
            self.cb_tracks.append(gtk.CheckButton(mapsObj.tracks[i]['name']))
            self.cb_tracks[i].set_active(mapsObj.tracks[i] in mapsObj.shown_tracks)
            self.cb_tracks[i].connect('toggled', self.showTracks)
            self.track_vbox.pack_start(self.cb_tracks[i])
        alignment.add(self.track_vbox)
        vbox.pack_start(alignment)
        frame.add(vbox)
        return frame

    def _createButtons(self):
        hbbox = gtk.HButtonBox()
        hbbox.set_border_width(10)
        hbbox.set_layout(gtk.BUTTONBOX_SPREAD)
        self.b_import = gtk.Button('_Import tracks')
        self.b_import.connect('clicked', self.importTracks)
        hbbox.pack_start(self.b_import)
        self.b_export = gtk.Button('_Export selected tracks')
        self.b_export.connect('clicked', self.exportTracks)
        hbbox.pack_start(self.b_export)
        self.b_gps_export = gtk.Button('Export _GPS track')
        self.b_gps_export.connect('clicked', self.exportGPS)
        hbbox.pack_start(self.b_gps_export)
        return hbbox

    def update_widgets(self):
        hasTracks = len(self.cb_tracks) > 0
        self.no_tracks.set_visible(not hasTracks)
        self.b_export.set_sensitive(hasTracks)
        if self.mapsObj.gps and len(self.mapsObj.gps.gps_points) > 0:
            self.b_gps_export.set_sensitive(True)
        else:
            self.b_gps_export.set_sensitive(False)

    def importTracks(self, w):
        tracks = openGPX()
        if tracks:
            self.mapsObj.tracks.extend(tracks)
            self.mapsObj.shown_tracks.extend(tracks)
            self.mapsObj.drawing_area.repaint()
            for track in tracks:
                self.cb_tracks.append(gtk.CheckButton(track['name']))
                self.cb_tracks[-1].set_active(True)
                self.cb_tracks[-1].connect('toggled', self.showTracks)
                self.cb_tracks[-1].show()
                self.track_vbox.pack_start(self.cb_tracks[-1])
        self.update_widgets()

    def exportTracks(self, w):
        tracksToExport = list()
        for i in range(len(self.mapsObj.tracks)):
            if self.cb_tracks[i].get_active():
                tracksToExport.append(self.mapsObj.tracks[i])
        if len(tracksToExport) > 0:
            saveGPX(tracksToExport)
        else:
            dialog = error_msg_non_blocking('No tracks', 'No tracks to export')
            dialog.connect('response', lambda dialog, response: dialog.destroy())
            dialog.show()

    def exportGPS(self, w):
        if self.mapsObj.gps and len(self.mapsObj.gps.gps_points) > 0:
            saveGPX([self.mapsObj.gps.gps_points])
        else:
            dialog = error_msg_non_blocking('No GPS points', 'No GPS points to save')
            dialog.connect('response', lambda dialog, response: dialog.destroy())
            dialog.show()

    def showTracks(self, w):
        tracksToShow = list()
        for i in range(len(self.mapsObj.tracks)):
            if self.cb_tracks[i].get_active():
                tracksToShow.append(self.mapsObj.tracks[i])
        self.mapsObj.shown_tracks = tracksToShow
        self.mapsObj.drawing_area.repaint()
