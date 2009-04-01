#!/usr/bin/env python
import math
import threading

import pygtk
pygtk.require('2.0')
import gtk, gobject

import mapUtils
import googleMaps
import mapTools
from gtkThread import do_gui_operation
from mapConst import *

def nice_round(f):
    n=math.ceil(math.log(f,10))
    p=f/10**n
    if p>0.5:
        p=1.0
    elif p>0.2:
        p=0.5
    else:
        p=0.2
    return p*10**n

class DLWindow(gtk.Window):
    def __init__(self, coord, kmx,kmy, layer):
        def lbl(text):
            l=gtk.Label(text)
            l.set_justify(gtk.JUSTIFY_RIGHT)
            return l        
        print "DLWindow(",coord,kmx,kmy,layer,')'
        kmx=nice_round(kmx)
        kmy=nice_round(kmy)
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
            xmin,ymin=top_left[0]
            xmax,ymax=bottom_right[0]
            for x in xrange(xmin,xmax+1):
                for y in xrange(ymin,ymax+1):
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

class MainWindow(gtk.Window):

    center = ((0,0),(128,128))
    draging_start = (0, 0)
    current_zoom_level = MAP_MAX_ZOOM_LEVEL
    default_text = "Enter location here!"
    show_panels = True

    def error_msg(self, msg, buttons=gtk.BUTTONS_OK):
        dialog = gtk.MessageDialog(self,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                gtk.MESSAGE_ERROR, buttons, msg)
        resp = dialog.run()
        dialog.destroy()
        return resp

    def do_scale(self, pos, pointer=None, force=False):
        pos = round(pos, 0)
        if (pos == round(self.scale.get_value(), 0)) and not force:
            return
        self.scale.set_value(pos)

        if (pointer == None):
            fix_tile, fix_offset = self.center
        else:
            rect = self.drawing_area.get_allocation()
            da_center = (rect.width / 2, rect.height / 2)

            fix_tile = self.center[0]
            fix_offset = self.center[1][0] + (pointer[0] - da_center[0]), \
                         self.center[1][1] + (pointer[1] - da_center[1])

            fix_tile, fix_offset = \
                mapUtils.tile_adjustEx(self.current_zoom_level,
                                       fix_tile, fix_offset)

        scala = 2 ** (self.current_zoom_level - pos)
        x = int((fix_tile[0] * TILES_WIDTH  + fix_offset[0]) * scala)
        y = int((fix_tile[1] * TILES_HEIGHT + fix_offset[1]) * scala)
        if (pointer != None) and not force:
            x = x - (pointer[0] - da_center[0])
            y = y - (pointer[1] - da_center[1])

        self.center = (x / TILES_WIDTH, y / TILES_HEIGHT), \
                      (x % TILES_WIDTH, y % TILES_HEIGHT)

        self.current_zoom_level = pos
        self.drawing_area.queue_draw()

    def get_zoom_level(self):
        return int(self.scale.get_value())

    # Automatically display after selecting
    def on_completion_match(self, completion, model, iter):
        self.entry.set_text(model[iter][0])
        self.confirm_clicked(self)

    # Clean out the entry box if text = default
    def clean_entry(self, *args):
        if (self.entry.get_text() == self.default_text):
            self.entry.set_text("")
            self.entry.grab_focus()

    # Reset the default text if entry is empty
    def default_entry(self, *args):
        if (self.entry.get_text().strip() == ''):
            self.entry.set_text(self.default_text)

    # Handles the change event of the ComboBox
    def changed_combo(self, *args):
        str = self.entry.get_text()
        if (str.endswith(SEPARATOR)):
            self.entry.set_text(str.strip())
            self.confirm_clicked(self)

    # Show the combo list if is not empty
    def combo_popup(self):
        if self.combo.get_model().get_iter_root() != None:
            self.combo.popup()

    # Handles the pressing of arrow keys
    def key_press_combo(self, w, event):
        if event.keyval in [65362, 65364]:
            self.combo_popup()
            return True

    # Create a gtk Menu with the given items
    def gtk_menu(self, listItems):
        myMenu = gtk.Menu()
        for str in listItems:
            # An empty item inserts a separator
            if str == "":
                menu_items = gtk.MenuItem()
            else:
                menu_items = gtk.MenuItem(str)
            myMenu.append(menu_items)
            menu_items.connect("activate", self.menu_item_response, str)
            menu_items.show()
        return myMenu

    # Handles the events in the Tools buttons
    def tools_button_event(self, w, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            w.popup(None, None, None, 1, event.time)
        elif event.type == gtk.gdk.KEY_PRESS and \
             event.keyval in [65293, 32]:
            self.menu_tools(TOOLS_MENU[0])

    def set_completion(self):
        completion = gtk.EntryCompletion()
        completion.connect('match-selected', self.on_completion_match)
        self.entry.set_completion(completion)
        completion.set_model(self.ctx_map.completion_model())
        completion.set_text_column(0)
        self.completion = completion
        # Populate the dropdownlist
        self.combo.set_model(self.ctx_map.completion_model(SEPARATOR))

    def confirm_clicked(self, button):
        location = self.entry.get_text()
        if (0 == len(location)):
            self.error_msg("Need location")
            self.entry.grab_focus()
            return
        if (location == self.default_text):
            self.clean_entry(self)
        else:
            locations = self.ctx_map.get_locations()
            if (not location in locations.keys()):
                if self.cb_offline.get_active():
                    if self.error_msg("Offline mode, cannot do search!" + \
                                      "      Would you like to get online?",
                                      gtk.BUTTONS_YES_NO) != gtk.RESPONSE_YES:
                        self.combo_popup()
                        return
                self.cb_offline.set_active(False)
                mapUtils.force_repaint()

                location = self.ctx_map.search_location(location)
                if (location[:6] == "error="):
                    self.error_msg(location[6:])
                    self.entry.grab_focus()
                    return

                self.entry.set_text(location)
                self.set_completion()
                coord = self.ctx_map.get_locations()[location]
            else:
                coord = locations[location]
            print "%s at %f, %f" % (location, coord[0], coord[1])

            self.center = mapUtils.coord_to_tile(coord)
            self.current_zoom_level = coord[2]
            self.do_scale(coord[2], force=True)

    def layer_changed(self, w):
        online = not self.cb_offline.get_active()
        self.layer = w.get_active()
        self.ctx_map.switch_layer(self.layer,online)
        self.drawing_area.queue_draw()

    def download_clicked(self,w):
        coord=mapUtils.tile_to_coord(self.center, self.current_zoom_level)
        rect = self.drawing_area.get_allocation()
        km_px=mapUtils.km_per_pixel(coord)
        dlw=DLWindow(coord, km_px*rect.width, km_px*rect.height, self.layer)
        dlw.show()

    # Creates a comboBox that will contain the locations
    def __create_combo_box(self):
        combo = gtk.combo_box_entry_new_text()
        combo.connect('changed', self.changed_combo)
        combo.connect('key-press-event', self.key_press_combo)

        entry = combo.child
        # Start search after hit 'ENTER'
        entry.connect('activate', self.confirm_clicked)
        # Launch clean_entry for all the signals/events below
        entry.connect("button-press-event", self.clean_entry)
        entry.connect("cut-clipboard", self.clean_entry)
        entry.connect("copy-clipboard", self.clean_entry)
        entry.connect("paste-clipboard", self.clean_entry)
        entry.connect("move-cursor", self.clean_entry)
        # Launch the default_entry on the focus out
        entry.connect("focus-out-event", self.default_entry)
        self.entry = entry
        return combo

    # Creates the box that packs the comboBox & buttons
    def __create_upper_box(self):
        hbox = gtk.HBox(False, 5)

        gtk.stock_add([(gtk.STOCK_PREFERENCES, "", 0, 0, "")])
        button = gtk.Button(stock=gtk.STOCK_PREFERENCES)
        menu = self.gtk_menu(TOOLS_MENU)
        button.connect_object("event", self.tools_button_event, menu)
        hbox.pack_start(button, False)

        self.combo = self.__create_combo_box()
        hbox.pack_start(self.combo)

        bbox = gtk.HButtonBox()
        button_go = gtk.Button(stock='gtk-ok')
        button_go.connect('clicked', self.confirm_clicked)
        bbox.add(button_go)

        hbox.pack_start(bbox, False, True, 15)
        return hbox

    # Creates the box with the CheckButtons
    def __create_check_buttons(self):
        hbox = gtk.HBox(False, 10)

        self.cb_offline = gtk.CheckButton("Offlin_e")
        self.cb_offline.set_active(True)
        hbox.pack_start(self.cb_offline)

        self.cb_forceupdate = gtk.CheckButton("_Force update")
        self.cb_forceupdate.set_active(False)
        hbox.pack_start(self.cb_forceupdate)

        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_SPREAD)
        gtk.stock_add([(gtk.STOCK_HARDDISK, "_Download", 0, 0, "")])
        button = gtk.Button(stock=gtk.STOCK_HARDDISK)
        button.connect('clicked', self.download_clicked)
        bbox.add(button)

        self.cmb_layer = gtk.combo_box_new_text()
        for w in LAYER_NAMES:
            self.cmb_layer.append_text(w)
        self.cmb_layer.set_active(0)
        self.cmb_layer.connect('changed',self.layer_changed)
        bbox.add(self.cmb_layer)
        
        hbox.pack_start(bbox)
        return hbox

    def __create_top_paned(self):
        frame = gtk.Frame("Query")
        vbox = gtk.VBox(False, 5)
        vbox.set_border_width(5)
        vbox.pack_start(self.__create_upper_box())
        vbox.pack_start(self.__create_check_buttons())
        frame.add(vbox)
        return frame

    def __create_left_paned(self):
        scale = gtk.VScale()
        scale.set_range(MAP_MIN_ZOOM_LEVEL, MAP_MAX_ZOOM_LEVEL)
        # scale.set_inverted(True)
        scale.set_property("update-policy", gtk.UPDATE_DISCONTINUOUS)
        scale.set_size_request(30, -1)
        scale.set_increments(1,1)
        scale.set_digits(0)
        scale.set_value(MAP_MAX_ZOOM_LEVEL)
        scale.connect("change-value", self.scale_change_value)
        scale.show()
        self.scale = scale
        return scale

    def __create_right_paned(self):
        da = gtk.DrawingArea()
        self.drawing_area = da
        da.connect("expose_event", self.expose_cb)
        da.add_events(gtk.gdk.SCROLL_MASK)
        da.connect("scroll-event", self.scroll_cb)

        da.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        da.add_events(gtk.gdk.BUTTON_RELEASE_MASK)
        da.add_events(gtk.gdk.BUTTON1_MOTION_MASK)

        menu = self.gtk_menu(["Zoom In", "Zoom Out", "Center map here", 
                              "Reset", "", "Batch Download"])

        da.connect_object("event", self.da_click_events, menu)
        da.connect('button-press-event', self.da_button_press)
        da.connect('button-release-event', self.da_button_release)
        da.connect('motion-notify-event', self.da_motion)
        da.show()
        return self.drawing_area

    def do_zoom(self, value, doForce=False):
        if (MAP_MIN_ZOOM_LEVEL <= value <= MAP_MAX_ZOOM_LEVEL):
            self.do_scale(value, self.drawing_area.get_pointer(), doForce)

    def menu_tools(self, strName):
        for intPos in range(len(TOOLS_MENU)):
            if strName.startswith(TOOLS_MENU[intPos]):
                mapTools.main(self, self.ctx_map.configpath, intPos)
                return True

    # All the actions for the menu items
    def menu_item_response(self, w, strName):
        if strName.startswith("Zoom Out"):
            self.do_zoom(self.scale.get_value() + 1, True)
        elif strName.startswith("Zoom In"):
            self.do_zoom(self.scale.get_value() - 1, True)
        elif strName.startswith("Center map"):
            self.do_zoom(self.scale.get_value(), True)
        elif strName.startswith("Reset"):
            self.do_zoom(MAP_MAX_ZOOM_LEVEL)
        elif strName.startswith("Batch Download"):
            self.download_clicked(w)
        else:
            self.menu_tools(strName)

    # Change the mouse cursor over the drawing_area
    def da_set_cursor(self, dCursor = gtk.gdk.HAND1):
        cursor = gtk.gdk.Cursor(dCursor)
        self.drawing_area.window.set_cursor(cursor)

    # Handles Right & Double clicks events in the drawing_area
    def da_click_events(self, w, event):
        # Right-Click event shows the popUp menu
        if (event.type == gtk.gdk.BUTTON_PRESS) and (event.button != 1):
            w.popup(None, None, None, event.button, event.time)
        # Double-Click event Zoom In
        elif (event.type == gtk.gdk._2BUTTON_PRESS):
            self.do_zoom(self.scale.get_value() - 1, True)

    # Handles left (press click) event in the drawing_area
    def da_button_press(self, w, event):
        if (event.button == 1):
            self.draging_start = (event.x, event.y)
            self.da_set_cursor(gtk.gdk.FLEUR)

    # Handles left (release click) event in the drawing_area
    def da_button_release(self, w, event):
        if (event.button == 1):
            self.da_set_cursor()

    # Handles the mouse motion over the drawing_area
    def da_motion(self, w, event):
        x = event.x
        y = event.y
        if (x < 0) or (y < 0):
            return

        rect = self.drawing_area.get_allocation()
        if (x > rect.width) or (y > rect.height):
            return

        #print "mouse move: (%d, %d)" % (x, y)

        center_tile = self.center[0]
        self.center[1]

        center_offset = (self.center[1][0] + (self.draging_start[0] - x),
                         self.center[1][1] + (self.draging_start[1] - y))
        self.center = mapUtils.tile_adjustEx(self.get_zoom_level(),
                         center_tile, center_offset)
        self.draging_start = (x, y)
        self.drawing_area.queue_draw()
        # print "new draging_start: (%d, %d)" % self.draging_start
        # print "center: %d, %d, %d, %d" % (self.center[0][0],
        #         self.center[0][1],
        #         self.center[1][0],
        #         self.center[1][1])

    def expose_cb(self, drawing_area, event):
        online = not self.cb_offline.get_active()
        force_update = self.cb_forceupdate.get_active()
        rect = drawing_area.get_allocation()
        zl = self.get_zoom_level()
        mapUtils.do_expose_cb(self, zl, self.center, rect, online,
                              force_update, self.drawing_area.style.black_gc,
                              event.area)

    def scroll_cb(self, widget, event):
        if (event.direction == gtk.gdk.SCROLL_UP):
            self.do_zoom(self.scale.get_value() - 1)
        else:
            self.do_zoom(self.scale.get_value() + 1)

    def scale_change_value(self, range, scroll, value):
        if (MAP_MIN_ZOOM_LEVEL <= value <= MAP_MAX_ZOOM_LEVEL):
            self.do_scale(value)
        return

    # Handles the pressing of F11 & F12
    def full_screen(self, w, event):
        if event.keyval == 65480:
            if self.get_decorated():
                self.set_keep_above(True)
                self.set_decorated(False)
                self.maximize()
            else:
                self.set_keep_above(False)
                self.set_decorated(True)
                self.unmaximize()
        elif event.keyval == 65481:
            if self.show_panels:
                self.left_panel.hide()
                self.top_panel.hide()
            else:
                self.left_panel.show()
                self.top_panel.show()
            self.show_panels = not self.show_panels

    def __init__(self, parent=None):
        self.ctx_map = googleMaps.GoogleMaps()
        self.layer=0
        gtk.Window.__init__(self)
        try:
            self.set_screen(parent.get_screen())
        except AttributeError:
            self.connect("destroy", lambda *w: gtk.main_quit())

        self.connect('key-press-event', self.full_screen)
        vpaned = gtk.VPaned()
        hpaned = gtk.HPaned()
        self.top_panel = self.__create_top_paned()
        self.left_panel = self.__create_left_paned()

        vpaned.pack1(self.top_panel, False, False)
        hpaned.pack1(self.left_panel, False, False)
        hpaned.pack2(self.__create_right_paned(), True, True)
        vpaned.add2(hpaned)

        self.add(vpaned)
        self.set_title(" GMapCatcher ")
        self.set_border_width(10)
        self.set_size_request(450, 400)
        self.set_completion()
        self.default_entry()
        self.show_all()

        self.da_set_cursor()
        self.entry.grab_focus()

def main():
    MainWindow()
    gtk.main()

if __name__ == "__main__":
    main()
