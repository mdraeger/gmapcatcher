# -*- coding: utf-8 -*-
## @package gmapcatcher.widgets.widDrawingArea
# DrawingArea widget used to display the map

import gtk
import pango
import math
import gmapcatcher.mapUtils as mapUtils
from gmapcatcher.mapConst import *
from threading import Timer

ternary = lambda a, b, c: (b, c)[not a]


## This widget is where the map is drawn
class DrawingArea(gtk.DrawingArea):
    center = ((0, 0), (128, 128))
    draging_start = (0, 0)
    myThread = None
    isPencil = False

    def __init__(self):
        super(DrawingArea, self).__init__()

        self.visualdl_gc = False
        self.scale_gc = False
        self.arrow_gc = False

        self.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.connect('button-press-event', self.da_button_press)

        self.add_events(gtk.gdk.BUTTON_RELEASE_MASK)
        self.connect('button-release-event', self.da_button_release)

    ## Change the mouse cursor over the drawing_area
    def da_set_cursor(self, dCursor=gtk.gdk.HAND1):
        cursor = gtk.gdk.Cursor(dCursor)
        self.window.set_cursor(cursor)
        self.isPencil = (dCursor == gtk.gdk.PENCIL)

    ## Handles left (press click) event in the drawing_area
    def da_button_press(self, w, event):
        if (event.button == 1):
            self.draging_start = (event.x, event.y)
            if not self.isPencil:
                self.da_set_cursor(gtk.gdk.FLEUR)

    ## Handles left (release click) event in the drawing_area
    def da_button_release(self, w, event):
        if (event.button == 1):
            if not self.isPencil:
                self.da_set_cursor()

    ## Jumps in the drawing_area
    def da_jump(self, intDirection, zoom, doBigJump=False):
        # Left  = 1  Up   = 2
        # Right = 3  Down = 4
        intJump = 10
        if doBigJump:
            intJump = intJump * 10

        self.draging_start = (intJump * (intDirection == 3),
                              intJump * (intDirection == 4))
        self.da_move(intJump * (intDirection == 1),
                     intJump * (intDirection == 2), zoom)

    ## Move the drawing_area
    def da_move(self, x, y, zoom):
        rect = self.get_allocation()
        if (0 <= x <= rect.width) and (0 <= y <= rect.height):
            offset = (self.center[1][0] + (self.draging_start[0] - x),
                      self.center[1][1] + (self.draging_start[1] - y))
            self.center = mapUtils.tile_adjustEx(zoom, self.center[0], offset)
            self.draging_start = (x, y)
            self.repaint()

    ## Scale in the drawing area (zoom in or out)
    def do_scale(self, zoom, current_zoom_level, doForce, dPointer):
        if (zoom == current_zoom_level) and not doForce:
            return

        rect = self.get_allocation()
        da_center = (rect.width // 2, rect.height // 2)
        if dPointer:
            fix_tile, fix_offset = mapUtils.pointer_to_tile(
                rect, dPointer, self.center, current_zoom_level
            )
        else:
            fix_tile, fix_offset = self.center

        scala = 2 ** (current_zoom_level - zoom)
        x = int((fix_tile[0] * TILES_WIDTH + fix_offset[0]) * scala)
        y = int((fix_tile[1] * TILES_HEIGHT + fix_offset[1]) * scala)
        if dPointer and not doForce:
            x = x - (dPointer[0] - da_center[0])
            y = y - (dPointer[1] - da_center[1])

        self.center = (x / TILES_WIDTH, y / TILES_HEIGHT), \
                      (x % TILES_WIDTH, y % TILES_HEIGHT)
        self.repaint()

    ## Repaint the drawing area
    def repaint(self):
        self.queue_draw()

    ## Convert coord to screen
    def coord_to_screen(self, x, y, zl):
        mct = mapUtils.coord_to_tile((x, y, zl))
        xy = mapUtils.tile_coord_to_screen(
            (mct[0][0], mct[0][1], zl), self.get_allocation(), self.center
        )
        if xy:
            for x, y in xy:
                return (x + mct[1][0], y + mct[1][1])

    ## Set the Graphics Context used in the visual download
    def set_visualdl_gc(self):
        if not self.visualdl_gc:
            fg_col = gtk.gdk.color_parse("#0F0")
            bg_col = gtk.gdk.color_parse("#0BB")
            self.visualdl_gc = self.window.new_gc(
                    fg_col, bg_col, None, gtk.gdk.COPY,
                    gtk.gdk.SOLID, None, None, None,
                    gtk.gdk.INCLUDE_INFERIORS,
                    0, 0, 0, 0, True, 3, gtk.gdk.LINE_DOUBLE_DASH,
                    gtk.gdk.CAP_NOT_LAST, gtk.gdk.JOIN_ROUND)
            self.visualdl_gc.set_dashes(0, [3])
            self.visualdl_gc.set_rgb_fg_color(fg_col)
            self.visualdl_gc.set_rgb_bg_color(bg_col)
            self.visualdl_lo = pango.Layout(self.get_pango_context())
            self.visualdl_lo.set_font_description(
                pango.FontDescription("sans normal 12"))

    ## Set the Graphics Context used in the scale
    def set_scale_gc(self):
        if not self.scale_gc:
            fg_scale = gtk.gdk.color_parse("#000")
            bg_scale = gtk.gdk.color_parse("#FFF")
            self.scale_gc = self.window.new_gc(
                    fg_scale, bg_scale, None, gtk.gdk.INVERT,
                    gtk.gdk.SOLID, None, None, None,
                    gtk.gdk.INCLUDE_INFERIORS,
                    0, 0, 0, 0, True, 3, gtk.gdk.LINE_SOLID,
                    gtk.gdk.CAP_NOT_LAST, gtk.gdk.JOIN_MITER)
            self.scale_gc.set_rgb_bg_color(bg_scale)
            self.scale_gc.set_rgb_fg_color(fg_scale)
            self.scale_lo = pango.Layout(self.get_pango_context())
            self.scale_lo.set_font_description(
                pango.FontDescription("sans normal 10"))

    ## Set the graphics context for the gps arrow
    def set_arrow_gc(self):
        if not self.arrow_gc:
            fg_arrow = gtk.gdk.color_parse("#777")
            bg_arrow = gtk.gdk.color_parse("#FFF")
            self.arrow_gc = self.window.new_gc(
                    fg_arrow, bg_arrow, None, gtk.gdk.INVERT,
                    gtk.gdk.SOLID, None, None, None,
                    gtk.gdk.INCLUDE_INFERIORS,
                    0, 0, 0, 0, True, 2, gtk.gdk.LINE_SOLID,
                    gtk.gdk.CAP_NOT_LAST, gtk.gdk.JOIN_MITER)
            self.arrow_gc.set_rgb_bg_color(bg_arrow)
            self.arrow_gc.set_rgb_fg_color(fg_arrow)

    ## Draws a circle
    def draw_circle(self, screen_coord, gc):
        radius = 10
        self.window.draw_arc(
            gc, True, screen_coord[0] - radius, screen_coord[1] - radius,
            radius * 2, radius * 2, 0, 360 * 64
        )

    ## Draws a point
    def draw_point(self, screen_coord, gc):
        self.window.draw_point(
            gc, screen_coord[0], screen_coord[1]
        )

    # ## Draws a line for ruler
    # def draw_line(self, gc, from_coord, to_coord, dist_str, zl):
    #     ini = self.coord_to_screen(from_coord[0], from_coord[1], zl)
    #     end = self.coord_to_screen(to_coord[0], to_coord[1], zl)
    #     if ini and end:
    #         self.window.draw_line(gc, ini[0], ini[1], end[0], end[1])
    #         if dist_str:
    #             pangolayout = self.create_pango_layout("")
    #             pangolayout.set_text(dist_str)
    #             self.wr_pltxt(gc, end[0], end[1], pangolayout)

    ## Draws a circle as starting point for ruler
    def draw_stpt(self, mcoord, zl):
        radius = 5
        gc = self.scale_gc
        screen_coord = self.coord_to_screen(mcoord[0], mcoord[1], zl)
        self.window.draw_arc(
            gc, True, screen_coord[0] - radius, screen_coord[1] - radius,
            radius * 2, radius * 2, 0, 360 * 64
        )

    ## Draws an image
    def draw_image(self, screen_coord, img, width, height):
        self.window.draw_pixbuf(
            self.style.black_gc, img, 0, 0,
            screen_coord[0] - width / 2, screen_coord[1] - height / 2,
            width, height
        )

    def w_draw_line(self, gc, x1, y1, x2, y2):
        self.window.draw_line(gc, int(x1), int(y1), int(x2), int(y2))

    def draw_arrow(self, screen_coord, direction):
        arrow_length = 50
        self.set_arrow_gc()
        rad = math.radians(direction)
        sin = math.sin(rad)
        cos = math.cos(rad)

        arrowtop = (screen_coord[0] + arrow_length * sin, screen_coord[1] - arrow_length * cos)

        self.w_draw_line(self.arrow_gc,
                screen_coord[0],
                screen_coord[1],
                arrowtop[0],
                arrowtop[1])
        # TODO: Arrow pointers
        # self.w_draw_line(self.arrow_gc,
        #         arrowtop[0], arrowtop[1],
        #         arrowtop[0] + 7 * math.cos(direction + 3 * math.pi / 4.0),
        #         arrowtop[1] + 7 * math.sin(direction + 3 * math.pi / 4.0))
        # self.w_draw_line(self.arrow_gc,
        #         arrowtop[0], arrowtop[1],
        #         arrowtop[0] + 7 * math.cos(direction - 3 * math.pi / 4.0),
        #         arrowtop[1] + 7 * math.sin(direction - 3 * math.pi / 4.0))

    ## Draws the marker
    def draw_marker(self, conf, mcoord, zl, img, pixDim, marker_name):
        screen_coord = self.coord_to_screen(mcoord[0], mcoord[1], zl)
        if screen_coord:
            gc = self.scale_gc
            cPos = marker_name.find('#')
            if (cPos > -1):
                try:
                    my_gc = self.window.new_gc()
                    color = gtk.gdk.color_parse(marker_name[cPos:cPos + 7])
                    my_gc.set_rgb_fg_color(color)
                    gc = my_gc
                except:
                    pass
            if marker_name.startswith('point'):
                self.draw_point(screen_coord, gc)
            elif marker_name.startswith('circle'):
                self.draw_circle(screen_coord, gc)
            else:
                self.draw_image(screen_coord, img, pixDim, pixDim)
                if conf.show_marker_name:
                    # Display the Marker Name
                    gco = self.window.new_gc()
                    gco.set_rgb_fg_color(gtk.gdk.color_parse(conf.marker_font_color))

                    pangolayout = self.create_pango_layout(marker_name)
                    pangolayout.set_font_description(
                            pango.FontDescription(conf.marker_font_desc))
                    self.wr_pltxt(gco, screen_coord[0], screen_coord[1], pangolayout)

    ## Show the text
    def wr_pltxt(self, gc, x, y, pl):
        gc1 = self.window.new_gc()
        gc1.line_width = 2
        gc1.set_rgb_fg_color(gtk.gdk.color_parse("#000000"))
        self.window.draw_layout(gc1, x - 1, y - 1, pl)
        self.window.draw_layout(gc1, x, y - 1, pl)
        self.window.draw_layout(gc1, x + 1, y - 1, pl)
        self.window.draw_layout(gc1, x + 1, y, pl)
        self.window.draw_layout(gc1, x + 1, y + 1, pl)
        self.window.draw_layout(gc1, x, y + 1, pl)
        self.window.draw_layout(gc1, x - 1, y + 1, pl)
        self.window.draw_layout(gc1, x - 1, y, pl)
        self.window.draw_layout(gc, x, y, pl)

    ## Draw the second layer of elements
    def draw_overlay(self, zl, conf, crossPixbuf, dlpixbuf,
                    downloading=False, visual_dlconfig={},
                    marker=None, locations={}, entry_name="",
                    showMarkers=False, gps=None,
                    r_coord=[],
                    tracks=None):
        self.set_scale_gc()
        self.set_visualdl_gc()
        rect = self.get_allocation()
        middle = (rect.width / 2, rect.height / 2)
        full = (rect.width, rect.height)

        # Draw cross in the center
        if conf.show_cross:
            self.draw_image(middle, crossPixbuf, 12, 12)

        # Draw scale
        if conf.scale_visible:
            self.draw_scale(full, zl)

        if showMarkers:
            pixDim = marker.get_pixDim(zl)
            # Draw the selected location
            if (entry_name in locations.keys()):
                coord = locations.get(unicode(entry_name))
                screen_coord = self.coord_to_screen(coord[0], coord[1], zl)
                if screen_coord:
                    img = marker.get_marker_pixbuf(zl, 'marker1.png')
                    self.draw_image(screen_coord, img, pixDim, pixDim)
            else:
                coord = (None, None, None)

            # Draw the markers
            if len(marker.positions) < 1000:
                self.draw_markers(zl, marker, coord, conf, pixDim)
            else:
                if (self.myThread is not None):
                    self.myThread.cancel()
                self.myThread = Timer(0.5, self.draw_markers_thread, [zl, marker, coord, conf, pixDim])
                self.myThread.start()

        # Draw the Ruler lines
        if len(r_coord) >= 1:
            self.draw_ruler_lines(r_coord, zl, conf.gps_track_width)

        # Draw GPS position
        if gps and gps.gpsfix:
            location = gps.get_location()
            if location is not None and (zl <= conf.max_gps_zoom):
                img = gps.pixbuf
                screen_coord = self.coord_to_screen(location[0], location[1], zl)
                if screen_coord:
                    self.draw_image(screen_coord, img,
                        GPS_IMG_SIZE[0], GPS_IMG_SIZE[1])
                    if gps.gpsfix.speed >= 0.5:  # draw arrow only, if speed is over 0.5 knots
                        self.draw_arrow(screen_coord, gps.gpsfix.track)
            if conf.gps_track and len(gps.gps_points) > 1:
                self.draw_gps_line(gps.gps_points, zl, conf.gps_track_width)

        # Draw the downloading notification
        if downloading:
            self.window.draw_pixbuf(
                self.style.black_gc, dlpixbuf, 0, 0, 0, 0, -1, -1)

        if (visual_dlconfig != {}):
            self.draw_visual_dlconfig(visual_dlconfig, middle, full, zl)

        if tracks:
            self.draw_tracks(tracks, zl, conf.gps_track_width)

    def draw_markers(self, zl, marker, coord, conf, pixDim):
        img = marker.get_marker_pixbuf(zl)
        for string in marker.positions.keys():
            mpos = marker.positions[string]
            if (zl <= mpos[2]) and (mpos[0], mpos[1]) != (coord[0], coord[1]):
                self.draw_marker(conf, mpos, zl, img, pixDim, string)

    def draw_markers_thread(self, *args):
        try:
            self.draw_markers(args[0], args[1], args[2], args[3], args[4])
        except:
            pass

    def draw_scale(self, full, zl):
        scaledata = mapUtils.friendly_scale(zl)
        # some 'dirty' rounding seems necessary :-)
        scaled = ternary(scaledata[1] % 10 == 9, scaledata[1] + 1, scaledata[1])
        scaled -= ternary(scaled % 10000 == 1000, 1000, 0)
        scalestr = ternary(scaled > 9000,
                str(scaled // 1000) + " km", str(scaled) + " m")
        self.scale_lo.set_text(scalestr)
        self.window.draw_line(self.scale_gc, 10, full[1] - 10, 10, full[1] - 15)
        self.window.draw_line(self.scale_gc, 10, full[1] - 10, scaledata[0] + 10, full[1] - 10)
        self.window.draw_line(self.scale_gc, scaledata[0] + 10, full[1] - 10, scaledata[0] + 10, full[1] - 15)
        self.window.draw_layout(self.scale_gc, 15, full[1] - 25, self.scale_lo)

    def draw_visual_dlconfig(self, visual_dlconfig, middle, full, zl):
        sz = visual_dlconfig.get("sz", 4)
        # Draw a rectangle
        if visual_dlconfig.get("show_rectangle", False):
            width = visual_dlconfig.get("width_rect", 0)
            height = visual_dlconfig.get("height_rect", 0)
            if width > 0 and height > 0:
                self.window.draw_rectangle(
                    self.scale_gc, True,
                    visual_dlconfig.get("x_rect", 0),
                    visual_dlconfig.get("y_rect", 0),
                    width, height
                )
        # Draw the download utility
        elif visual_dlconfig.get("active", False):
            thezl = str(zl + visual_dlconfig.get("zl", -2))
            self.visualdl_lo.set_text(thezl)
            self.window.draw_rectangle(self.visualdl_gc, False,
                    middle[0] - full[0] / (sz * 2),
                    middle[1] - full[1] / (sz * 2), full[0] / sz, full[1] / sz)
            self.window.draw_layout(self.visualdl_gc,
                    middle[0] + full[0] / (sz * 2) - len(thezl) * 10,
                    middle[1] - full[1] / (sz * 2),
                    self.visualdl_lo)

        if visual_dlconfig.get('qd', 0) > 0:
            self.visualdl_lo.set_text(
                    str(visual_dlconfig.get('recd', 0)) + "/" +
                    str(visual_dlconfig.get('qd', 0)))
            if sz == 1:
                ypos = -15
            else:
                ypos = 0
            self.window.draw_layout(self.visualdl_gc,
                    middle[0],
                    middle[1] + full[1] / (sz * 2) + ypos,
                    self.visualdl_lo)

    def draw_line(self, points, color, zl, width, draw_distance=False):
        gc = self.style.black_gc
        gc.line_width = width
        gc.set_rgb_fg_color(gtk.gdk.color_parse(color))
        dist_str = None
        total_distance = 0
        for j in range(len(points) - 1):
            if draw_distance:
                distance = mapUtils.countDistanceFromLatLon(points[j], points[j + 1])
                total_distance += distance
                dist_str = '%.3f km \n%.3f km' % (distance, total_distance)
            ini = self.coord_to_screen(points[j][0], points[j][1], zl)
            end = self.coord_to_screen(points[j + 1][0], points[j + 1][1], zl)
            if ini and end:
                self.window.draw_line(gc, ini[0], ini[1], end[0], end[1])
                if dist_str:
                    pangolayout = self.create_pango_layout("")
                    pangolayout.set_text(dist_str)
                    self.wr_pltxt(gc, end[0], end[1], pangolayout)
        return gc

    def draw_ruler_lines(self, points, zl, track_width):
        color = '#00FF00'
        self.draw_line(points, color, zl, track_width, True)
        # for i in range(0, len(r) - 1):
        #     gc.set_rgb_fg_color(gtk.gdk.color_parse(colors[i % 4]))
        #     dist_str = '%.3f km' % mapUtils.countDistanceFromLatLon(r[i], r[i + 1])
        #     self.draw_line(gc, r[i], r[i + 1], dist_str, zl)

    def draw_gps_line(self, points, zl, track_width):
        color = '#FF0000'
        self.draw_line(points, color, zl, track_width, False)
        # for i in range(0, len(points) - 1):
        #     gc.set_rgb_fg_color(gtk.gdk.color_parse(color))
        #     self.draw_line(gc, points[i], points[i + 1], '', zl)

    def draw_tracks(self, tracks, zl, track_width, draw_distance=True):
        colors = ["#4444FF", "#FFFF00", "#FF00FF"]
        i = 0
        for track in tracks:
            color = colors[i % len(colors)]
            gc = self.draw_line(track['coords'], color, zl, track_width, draw_distance)
            screen_coord = self.coord_to_screen(track['coords'][0][0], track['coords'][0][1], zl)
            if screen_coord:
                pangolayout = self.create_pango_layout("")
                pangolayout.set_text(track['name'])
                self.wr_pltxt(gc, int(screen_coord[0]), int(screen_coord[1]), pangolayout)
            i += 1
        # print tracks
        # for points in tracks:
        #     screen_coord = self.coord_to_screen(track['coords'][j][0], track['coords'][j][1], zl)
        #     if screen_coord:
        #         pangolayout = self.create_pango_layout("")
        #         pangolayout.set_text(track['name'])
        #         self.wr_pltxt(gc, int(screen_coord[0]), int(screen_coord[1]), pangolayout)
        # self.draw_lines(tracks, colors, zl, gps_track_width, draw_distance=True)
        # if zl >= 10:
        #     minimum_distance = 10
        # elif zl >= 6:
        #     minimum_distance = 5
        # elif zl >= 4:
        #     minimum_distance = 1
        # elif zl >= 2:
        #     minimum_distance = 0.1
        # else:
        #     minimum_distance = 0.01
        # i = 0
        # for track in tracks:
        #     last_drawn = None
        #     old_length = 0
        #     new_length = 0
        #     gc.set_rgb_fg_color(gtk.gdk.color_parse(colors[i % 4]))
        #     for j in range(len(track['coords'])):
        #         if j != 0:
        #             new_length += mapUtils.countDistanceFromLatLon(track['coords'][j - 1], track['coords'][j])
        #         if j == 0:
        #             last_drawn = track['coords'][j]
        #             screen_coord = self.coord_to_screen(track['coords'][j][0], track['coords'][j][1], zl)
        #             if screen_coord:
        #                 pangolayout = self.create_pango_layout("")
        #                 pangolayout.set_text(track['name'])
        #                 self.wr_pltxt(gc, int(screen_coord[0]), int(screen_coord[1]), pangolayout)
        #         elif mapUtils.countDistanceFromLatLon(track['coords'][j], last_drawn) >= minimum_distance \
        #          or j == (len(track['coords']) - 1):
        #             if (new_length - old_length) > 1 and (new_length - old_length) > minimum_distance:
        #                 dist_str = '%.2f km' % new_length
        #                 old_length = new_length
        #             else:
        #                 dist_str = ''
        #             self.draw_line(gc, last_drawn, track['coords'][j], dist_str, zl)
        #             last_drawn = track['coords'][j]
        #     i = i + 1
