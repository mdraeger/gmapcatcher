import threading

import pygtk
pygtk.require('2.0')
import gtk, gobject

import mapUtils
import googleMaps
from mapConst import *
from gtkThread import do_gui_operation

class DLWindow(gtk.Window):
    def __init__(self, coord, kmx, kmy, layer):
        def lbl(text):
            l=gtk.Label(text)
            l.set_justify(gtk.JUSTIFY_RIGHT)
            return l
        print "DLWindow(",coord,kmx,kmy,layer,')'
        kmx = mapUtils.nice_round(kmx)
        kmy = mapUtils.nice_round(kmy)
        self.layer=layer
        gtk.Window.__init__(self)
        lat0=coord[0]
        lon0=coord[1]
        zoom0=max(MAP_MIN_ZOOM_LEVEL,coord[2]-3)
        zoom1=min(MAP_MAX_ZOOM_LEVEL,coord[2]+1)

        tbl=gtk.Table(rows=4, columns=4, homogeneous=False)
        tbl.set_col_spacings(10)
        tbl.set_row_spacings(10)

        tbl.attach(lbl("Center latitude:"),0,1,0,1)
        self.e_lat0=gtk.Entry()
        self.e_lat0.set_text("%.6f" % lat0)
        tbl.attach(self.e_lat0, 1,2,0,1)
        tbl.attach(lbl("longitude:"),2,3,0,1)
        self.e_lon0=gtk.Entry()
        self.e_lon0.set_text("%.6f" % lon0)
        tbl.attach(self.e_lon0, 3,4,0,1)

        tbl.attach(lbl("Area width (km):"),0,1,1,2)
        self.e_kmx=gtk.Entry()
        self.e_kmx.set_text("%.6g" % kmx)
        tbl.attach(self.e_kmx, 1,2,1,2)
        tbl.attach(lbl("Area height (km):"),2,3,1,2)
        self.e_kmy=gtk.Entry()
        self.e_kmy.set_text("%.6g" % kmy)
        tbl.attach(self.e_kmy, 3,4,1,2)

        tbl.attach(lbl("Zoom min:"),0,1,2,3)
        a_zoom0=gtk.Adjustment(zoom0,MAP_MIN_ZOOM_LEVEL,MAP_MAX_ZOOM_LEVEL,1)
        self.s_zoom0=gtk.SpinButton(a_zoom0)
        self.s_zoom0.set_digits(0)
        tbl.attach(self.s_zoom0, 1,2,2,3)
        tbl.attach(lbl("max:"),2,3,2,3)
        a_zoom1=gtk.Adjustment(zoom1,MAP_MIN_ZOOM_LEVEL,MAP_MAX_ZOOM_LEVEL,1)
        self.s_zoom1=gtk.SpinButton(a_zoom1)
        self.s_zoom1.set_digits(0)
        tbl.attach(self.s_zoom1, 3,4,2,3)

        self.b_download=gtk.Button(label="Download")
        tbl.attach(self.b_download, 1,2,3,4, xoptions=gtk.EXPAND|gtk.FILL, yoptions=0)
        self.b_download.connect('clicked', self.run)

        self.b_cancel=gtk.Button(stock='gtk-cancel')
        tbl.attach(self.b_cancel, 3,4,3,4, xoptions=gtk.EXPAND|gtk.FILL, yoptions=0)
        self.b_cancel.connect('clicked', self.cancel)
        self.b_cancel.set_sensitive(False)

        self.pbar=gtk.ProgressBar()
        tbl.attach(self.pbar, 0,4,4,5, xoptions=gtk.EXPAND|gtk.FILL, yoptions=0)

        self.add(tbl)

        self.set_title("GMapCatcher download")
        self.set_border_width(10)
        self.set_size_request(600, 300)

        self.todo=[]
        self.processing=False
        self.thr=None
        self.gmap=None
        self.connect('delete-event', self.on_delete)
        self.show_all()

    def run(self,w):
        if self.processing: return
        try:
            lat0=float(self.e_lat0.get_text())
            lon0=float(self.e_lon0.get_text())
            kmx=float(self.e_kmx.get_text())
            kmy=float(self.e_kmy.get_text())
            zoom0=self.s_zoom0.get_value_as_int()
            zoom1=self.s_zoom1.get_value_as_int()
            layer=self.layer
        except ValueError:
            d=gtk.MessageDialog(self,gtk.DIALOG_MODAL,gtk.MESSAGE_ERROR,gtk.BUTTONS_CLOSE,
                "Some field contain non-numbers")
            d.run()
            d.destroy()
        self.b_cancel.set_sensitive(True)
        self.b_download.set_sensitive(False)
        print ("lat0=%g lon0=%g kmx=%g kmy=%g zoom0=%d zoom1=%d layer=%d"
            % (lat0, lon0, kmx, kmy, zoom0, zoom1, layer))
        dlon=kmx*180/math.pi/(mapUtils.R_EARTH*math.cos(lat0*math.pi/180))
        dlat=kmy*180/math.pi/mapUtils.R_EARTH
        todo=[]
        if zoom0>zoom1: zoom0,zoom1=zoom1,zoom0
        for zoom in xrange(zoom1,zoom0-1,-1):
            top_left = mapUtils.coord_to_tile((lat0+dlat/2., lon0-dlon/2., zoom))
            bottom_right = mapUtils.coord_to_tile((lat0-dlat/2., lon0+dlon/2., zoom))
            world_tiles = mapUtils.tiles_on_level(zoom)
            xmin,ymin=top_left[0]
            xmax,ymax=bottom_right[0]
            for i in range((xmax-xmin+1+world_tiles)%world_tiles):
                x=(xmin+i)%world_tiles
                for j in range((ymax-ymin+1+world_tiles)%world_tiles):
                    y=(ymin+j)%world_tiles
                    todo.append((x,y,zoom))
        self.gmap=googleMaps.GoogleMaps(layer=layer) # creating our own gmap
        self.processing=True
        self.thr=threading.Thread(target=self.run_thread, args=(todo,))
        self.thr.start()

    def update_pbar(self, text, pos, maxpos):
        self.pbar.set_text(text)
        self.pbar.set_fraction(float(pos)/maxpos)

    def download_complete(self):
        self.update_pbar("Complete",0,1);
        self.processing=False
        self.b_cancel.set_sensitive(False)
        self.b_download.set_sensitive(True)

    def run_thread(self, todo):
        for i,q in enumerate(todo):
            if not self.processing: return
            do_gui_operation(self.update_pbar, "x=%d y=%d zoom=%d" % q, i, len(todo))
            self.gmap.get_tile_pixbuf(q, True, False)
        do_gui_operation(self.download_complete)

    def stop_thread(self):
        if self.thr and self.thr.isAlive():
            self.processing=False
            self.thr.join()
        self.thr=None

    def cancel(self,w):
        self.stop_thread()
        self.update_pbar("Canceled",0,1);
        self.b_cancel.set_sensitive(False)
        self.b_download.set_sensitive(True)

    def on_delete(self,*params):
        self.stop_thread()
        return False