#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       pytacle.py
#       
#       Copyright 2011 Daniel Mende <mail@c0decafe.de>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import ConfigParser
import math
import os
import platform
import shutil
import signal
import socket
import struct
import subprocess
import tempfile
import threading
import time

import pygtk
pygtk.require('2.0')

import gobject
import pango
import gtk
gtk.gdk.threads_init()

from mcc_mnc import codes

VERSION = "v0.2"
PLATFORM = platform.system()
DEBUG = False

#~ import pprint
#~ pp = pprint.PrettyPrinter(indent=4)

class pytacle(object):
    def __init__(self):
        signals = { 'main_window_delete_event'      : self.delete_event,
                    'main_window_destroy_event'     : self.destroy_event,
                    'on_quit_button_clicked'        : self.destroy_event,
                    'on_config_button_clicked'      : self.on_config_button_clicked,
                    'on_cancel_button_clicked'      : self.on_cancel_button_clicked,
                    'on_ok_button_clicked'          : self.on_ok_button_clicked,
                    'on_upstream_checkbutton_toggled'   :   self.on_upstream_checkbutton_toggled,
                    'on_record_button_toggled'      : self.on_record_button_toggled,
                    'on_crack_button_clicked'       : self.on_crack_button_clicked,
                    'on_decode_button_clicked'      : self.on_decode_button_clicked,
                    'on_scan_button_clicked'        : self.on_scan_button_clicked,
                    'on_scan_togglebutton_toggled'  : self.on_scan_togglebutton_toggled,
                    }
        builder = gtk.Builder()
        builder.add_from_file("windows.glade")
        builder.connect_signals(signals)
        self.main_window = builder.get_object("main_window")
        self.main_window.set_title(self.__class__.__name__)
        self.main_window.set_default_size(800, 600)
        
        self.source_combobox = builder.get_object("source_combobox")
        m = gtk.ListStore(gobject.TYPE_STRING)
        m.insert(0, ["USRP"])
        m.insert(0, ["RTLSDR"])
        self.source_combobox.set_model(m)
        cell = gtk.CellRendererText()
        self.source_combobox.pack_start(cell, True)
        self.source_combobox.add_attribute(cell, 'text', 0)
        self.source_combobox.set_active(0)
        self.record_outfile_2_hbox = builder.get_object("record_outfile_2_hbox")
        self.record_outfile_2_hbox.hide()
        self.record_outfile_2_hbox.set_no_show_all(True)
        self.record_outfile_1_entry = builder.get_object("record_outfile_1_entry")
        self.record_outfile_2_entry = builder.get_object("record_outfile_2_entry")
        self.record_filesize_label = builder.get_object("record_filesize_label")
        self.record_arfcn_entry = builder.get_object("record_arfcn_entry")
        self.upstream_checkbutton = builder.get_object("upstream_checkbutton")
        self.record_band_combobox = builder.get_object("record_band_combobox")
        m = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT64, gobject.TYPE_INT64)
        m.insert(0, ["GSM450", 259, 450600, 10000])
        m.insert(0, ["GSM480", 306, 479000, 10000])
        m.insert(0, ["GSM850", 128, 824200, 45000])
        m.insert(0, ["GSM900", 0, 890000, 45000])
        m.insert(0, ["GSM1800", 512, 1710200, 95000])
        m.insert(0, ["GSM1900", 512, 1850200, 80000])
        self.record_band_combobox.set_model(m)
        cell = gtk.CellRendererText()
        self.record_band_combobox.pack_start(cell, True)
        self.record_band_combobox.add_attribute(cell, 'text', 0)
        self.record_band_combobox.set_active(0)
        self.record_thread = None
        self.record_thread_running = False
        
        self.crack_infile_entry = builder.get_object("crack_infile_entry")
        self.crack_button = builder.get_object("crack_button")
        self.crack_thread = None
        
        self.decode_infile_entry = builder.get_object("decode_infile_entry")
        self.decode_key_entry = builder.get_object("decode_key_entry")
        self.decode_outfile_entry = builder.get_object("decode_outfile_entry")
        self.decode_button = builder.get_object("decode_button")
        self.decode_thread = None
        
        self.log_textview = builder.get_object("log_textview")
        self.log_textbuffer = builder.get_object("log_textbuffer")
        self.log_textbuffer.create_tag("status", foreground="black")
        self.log_textbuffer.create_tag("info", foreground="grey")
        self.log_textbuffer.create_tag("error", foreground="red")
        self.log_textbuffer.create_tag("sucess", foreground="black", weight=pango.WEIGHT_BOLD)
        
        self.config_window = builder.get_object("config_window")
        self.gsm_receive_usrp_entry = builder.get_object("gsm_receive_usrp_entry")
        self.gsm_receive_rtl_entry = builder.get_object("gsm_receive_rtl_entry")
        self.gsm_receive_entry = builder.get_object("gsm_receive_entry")
        self.gsmframecoder_entry = builder.get_object("gsmframecoder_entry")
        self.find_kc_entry = builder.get_object("find_kc_entry")
        self.toast_entry = builder.get_object("toast_entry")
        
        self.usrp_1_ip_entry = builder.get_object("usrp_1_ip_entry")
        self.usrp_2_ip_entry = builder.get_object("usrp_2_ip_entry")
        
        self.kraken_host_entry = builder.get_object("kraken_host_entry")
        self.kraken_port_entry = builder.get_object("kraken_port_entry")
        
        self.tempdir_entry = builder.get_object("tempdir_entry")
        
        self.parser = ConfigParser.ConfigParser()
        if os.path.isdir(os.path.expanduser("~/.%s" % self.__class__.__name__)):
            if os.path.isfile(os.path.expanduser("~/.%s/config" % self.__class__.__name__)):
                self.parser.read(os.path.expanduser("~/.%s/config" % self.__class__.__name__))
                if self.parser.has_section("dirs"):
                    self.dirs = dict(self.parser.items("dirs"))
                if self.parser.has_section("usrp"):
                    self.usrp = dict(self.parser.items("usrp"))
                if self.parser.has_section("kraken"):
                    self.kraken = dict(self.parser.items("kraken"))
                if self.parser.has_section("utils"):
                    self.utils = dict(self.parser.items("utils"))
        else:
            os.mkdir(os.path.expanduser("~/.%s" % self.__class__.__name__))
        
        if not "dirs" in dir(self):
            self.dirs = self.default_dirs()
        if not "usrp" in dir(self):
            self.usrp = self.default_usrp()
        if not "kraken" in dir(self):
            self.kraken = self.default_kraken()
        if not "utils" in dir(self):
            self.utils = self.default_utils()
        
        with os.popen("which python 2> /dev/null") as pipe:
            self.utils["python"] = pipe.read().strip("\n")
            
        self.update_dirs(self.dirs)
        self.update_usrp(self.usrp)
        self.update_kraken(self.kraken)
        self.update_utils(self.utils)        
        
        self.record_outfile_1_entry.set_text(tempfile.mktemp(prefix="pytacle_record_dl_", dir=self.dirs["tmp"]))
        self.record_outfile_2_entry.set_text(tempfile.mktemp(prefix="pytacle_record_ul_", dir=self.dirs["tmp"]))
        self.decode_outfile_entry.set_text(tempfile.mktemp(prefix="pytacle_decode_", dir=self.dirs["tmp"]))
        
        self.scan_window = builder.get_object("scan_window")
        self.scan_source_combobox = builder.get_object("scan_source_combobox")
        m = gtk.ListStore(gobject.TYPE_STRING)
        m.insert(0, ["USRP"])
        m.insert(0, ["RTLSDR"])
        self.scan_source_combobox.set_model(m)
        cell = gtk.CellRendererText()
        self.scan_source_combobox.pack_start(cell, True)
        self.scan_source_combobox.add_attribute(cell, 'text', 0)
        self.scan_source_combobox.set_active(0)
        self.scan_band_combobox = builder.get_object("scan_band_combobox")
        m = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT64, gobject.TYPE_INT64, gobject.TYPE_INT, gobject.TYPE_INT)
        m.insert(0, ["GSM450", 259, 450600, 10000, 259, 293])
        m.insert(0, ["GSM480", 306, 479000, 10000, 306, 340])
        m.insert(0, ["GSM850", 128, 824200, 45000, 128, 251])
        m.insert(0, ["GSM900", 0, 890000, 45000, 0, 124])
        m.insert(0, ["GSM1800", 512, 1710200, 95000, 512, 885])
        m.insert(0, ["GSM1900", 512, 1850200, 80000, 512, 810])
        self.scan_band_combobox.set_model(m)
        cell = gtk.CellRendererText()
        self.scan_band_combobox.pack_start(cell, True)
        self.scan_band_combobox.add_attribute(cell, 'text', 0)
        self.scan_band_combobox.set_active(0)
        self.scan_togglebutton = builder.get_object("scan_togglebutton")
        self.scan_thread = None
        self.scan_thread_running = False
        self.scan_textview = builder.get_object("scan_textview")
        self.scan_textbuffer = builder.get_object("scan_textbuffer")
        self.scan_arfcn_label = builder.get_object("scan_arfcn_label")
    
    def save_config(self):
        if not self.parser.has_section("utils"):
            self.parser.add_section("utils")
        self.parser.set("utils", "gsm_receive_usrp", self.utils["gsm_receive_usrp"])
        self.parser.set("utils", "gsm_receive_rtl", self.utils["gsm_receive_rtl"])
        self.parser.set("utils", "gsm_receive", self.utils["gsm_receive"])
        self.parser.set("utils", "gsmframecoder", self.utils["gsmframecoder"])
        self.parser.set("utils", "find_kc", self.utils["find_kc"])
        self.parser.set("utils", "toast", self.utils["toast"])
        if not self.parser.has_section("usrp"):
            self.parser.add_section("usrp")
        self.parser.set("usrp", "usrp_1_ip", self.usrp["usrp_1_ip"])
        #self.parser.set("usrp", "usrp_2_ip", self.usrp["usrp_2_ip"])
        if not self.parser.has_section("kraken"):
            self.parser.add_section("kraken")
        self.parser.set("kraken", "host", self.kraken["host"])
        self.parser.set("kraken", "port", self.kraken["port"])
        if not self.parser.has_section("dirs"):
            self.parser.add_section("dirs")
        self.parser.set("dirs", "tmp", self.dirs["tmp"])
        with open(os.path.expanduser("~/.%s/config" % self.__class__.__name__), 'w') as fp:
            self.parser.write(fp)
    
    def default_kraken(self):
        return { 'host'     : '127.0.0.1',
                 'port'     : '9666' }
    
    def update_kraken(self, kraken):
        self.kraken_host_entry.set_text(kraken["host"])
        self.kraken_port_entry.set_text(kraken["port"])
    
    def read_kraken(self):
        kraken = {}
        kraken["host"] = self.kraken_host_entry.get_text()
        kraken["port"] = self.kraken_port_entry.get_text()
        return kraken
    
    def default_dirs(self):
        return { 'tmp'  : '/tmp/' }
    
    def update_dirs(self, dirs):
        self.tempdir_entry.set_text(dirs["tmp"])
    
    def read_dirs(self):
        dirs = {}
        dirs["tmp"] = os.path.expanduser(self.tempdir_entry.get_text())
        if not os.path.isdir(dirs["tmp"]):
            self.log("Path '%s' not found" % dirs["tmp"], "error")
        else:
            tempfile.tempdir = dirs["tmp"]
        return dirs

    def default_usrp(self):
        return {    'usrp_1_ip'     :   '192.168.2.10',
                    #'usrp_2_ip'     :   '',
                    }
        
    def update_usrp(self, usrp):
        self.usrp_1_ip_entry.set_text(usrp["usrp_1_ip"])
        #self.usrp_2_ip_entry.set_text(usrp["usrp_2_ip"])
    
    def read_usrp(self):
        usrp = {}
        usrp["usrp_1_ip"] = self.usrp_1_ip_entry.get_text()
        #usrp["usrp_2_ip"] = self.usrp_2_ip_entry.get_text()
        return usrp

    def default_utils(self):
        utils = {}
        with os.popen("which gsm_receive_usrp.py 2> /dev/null") as pipe:
            utils["gsm_receive_usrp"] = pipe.read().strip("\n")
        with os.popen("which gsm_receive_rtl.py 2> /dev/null") as pipe:
            utils["gsm_receive_rtl"] = pipe.read().strip("\n")
        with os.popen("which gsm_reciever.py 2> /dev/null") as pipe:
            utils["gsm_receive"] = pipe.read().strip("\n")
        with os.popen("which gsmframecoder 2> /dev/null") as pipe:
            utils["gsmframecoder"] = pipe.read().strip("\n")
        with os.popen("which find_kc 2> /dev/null") as pipe:
            utils["find_kc"] = pipe.read().strip("\n")
        with os.popen("which toast 2> /dev/null") as pipe:
            utils["toast"] = pipe.read().strip("\n")
        return utils
    
    def update_utils(self, utils):
        self.gsm_receive_usrp_entry.set_text(utils["gsm_receive_usrp"])
        self.gsm_receive_rtl_entry.set_text(utils["gsm_receive_rtl"])
        self.gsm_receive_entry.set_text(utils["gsm_receive"])
        self.gsmframecoder_entry.set_text(utils["gsmframecoder"])
        self.find_kc_entry.set_text(utils["find_kc"])
        self.toast_entry.set_text(utils["toast"])
        
    def read_utils(self):
        utils = {}
        utils["gsm_receive_usrp"] = os.path.expanduser(self.gsm_receive_usrp_entry.get_text())
        if not os.path.isfile(utils["gsm_receive_usrp"]):
            self.log("File '%s' not found\n" % utils["gsm_receive_usrp"], "error")
        utils["gsm_receive_rtl"] = os.path.expanduser(self.gsm_receive_rtl_entry.get_text())
        if not os.path.isfile(utils["gsm_receive_rtl"]):
            self.log("File '%s' not found\n" % utils["gsm_receive_rtl"], "error")
        utils["gsm_receive"] = os.path.expanduser(self.gsm_receive_entry.get_text())
        if not os.path.isfile(utils["gsm_receive"]):
            self.log("File '%s' not found\n" % utils["gsm_receive"], "error")
        utils["gsmframecoder"] = os.path.expanduser(self.gsmframecoder_entry.get_text())
        if not os.path.isfile(utils["gsmframecoder"]):
            self.log("File '%s' not found\n" % utils["gsmframecoder"], "error")
        utils["find_kc"] = os.path.expanduser(self.find_kc_entry.get_text())
        if not os.path.isfile(utils["find_kc"]):
            self.log("File '%s' not found\n" % utils["find_kc"], "error")
        utils["toast"] = os.path.expanduser(self.toast_entry.get_text())
        if not os.path.isfile(utils["toast"]):
            self.log("File '%s' not found\n" % utils["toast"], "error")
        return utils
    
    def main(self):
        self.log("This is %s version %s by Daniel Mende - mail@c0decafe.de\n" % (self.__class__.__name__, VERSION))
        self.log("Running on %s\n\n" % (PLATFORM))
        self.main_window.show_all()
        gtk.gdk.threads_enter()
        gtk.main()
        gtk.gdk.threads_leave()
    
    def log(self, text, tag="status"):
        self.log_textbuffer.insert_with_tags_by_name(self.log_textbuffer.get_end_iter(), text, tag)
        self.log_textview.scroll_to_iter(self.log_textbuffer.get_end_iter(), 0.0)
    
    def log_t(self, text, tag="status"):
        gtk.gdk.threads_enter()
        self.log(text, tag)
        gtk.gdk.threads_leave()
    
    def delete_event(self, widget, event, data=None):
        return False
        
    def destroy_event(self, widget, data=None):  
        if self.record_thread:
            if self.record_thread.isAlive():
                self.log("Shutting down recording...", "error")
                self.record_thread_running = False
                self.record_thread.join()
        #~ if self.crack_thread:
            #~ if self.crack_thread.isAlive():
                #~ self.log("Joining crack thread....", "error")
                #~ self.crack_thread.join()
        gtk.main_quit()
        self.save_config()
    
    def on_config_button_clicked(self, widget, data=None):
        self.config_window.show_all()

    def on_cancel_button_clicked(self, widget, data=None):
        self.config_window.hide()
    
    def on_ok_button_clicked(self, widget, data=None):
        self.utils = self.read_utils()
        self.kraken = self.read_kraken()
        self.dirs = self.read_dirs()
        self.config_window.hide()
    
    def on_upstream_checkbutton_toggled(self, widget, data=None):
        if widget.get_active():
            self.record_outfile_2_hbox.set_no_show_all(False)
            self.record_outfile_2_hbox.show()
        else:
            self.record_outfile_2_hbox.hide()
            self.record_outfile_2_hbox.set_no_show_all(True)

    def on_record_button_toggled(self, widget, data=None):
        if not widget.get_active():
            self.record_thread_running = False
            if self.record_thread:
                if self.record_thread.isAlive():
                    self.record_thread.join()
        else:
            self.record_thread_running = True
            self.record_thread = threading.Thread(target=self.record)
            self.record_thread.start()
    
    def record(self):
        (name, offset, start, diff) = self.record_band_combobox.get_model()[self.record_band_combobox.get_active()]
        arfcn = int(self.record_arfcn_entry.get_text())
        freq = (start + (arfcn - offset) * 200 + diff) * 1000
        outfile = self.record_outfile_1_entry.get_text()
        (source,) = self.source_combobox.get_model()[self.source_combobox.get_active()]
        if source == "USRP":
            cmd = [self.utils["python"], self.utils["gsm_receive_usrp"], "-f", str(freq), "-k", "\"00 00 00 00 00 00 00 00\"", "-o", outfile]
            proc = subprocess.Popen(cmd, cwd=os.path.dirname(self.utils["gsm_receive_usrp"]))
        elif source == "RTLSDR":
            cmd = [self.utils["python"], self.utils["gsm_receive_rtl"], "-f", str(freq), "-k", "\"00 00 00 00 00 00 00 00\"", "-o", outfile]
            proc = subprocess.Popen(cmd, cwd=os.path.dirname(self.utils["gsm_receive_rtl"]))
        else:
            return
        time.sleep(2)
        while self.record_thread_running:
            self.record_filesize_label.set_text("%d Byte" % os.path.getsize(outfile))
            time.sleep(0.5)
        proc.kill()
        self.crack_infile_entry.set_text(outfile)
    
    def on_crack_button_clicked(self, widget, data=None):
        self.crack_thread = threading.Thread(target=self.crack)
        self.crack_button.set_property("sensitive", False)
        self.crack_thread.start()
        
    def crack(self):
        infile = os.path.expanduser(self.crack_infile_entry.get_text())
        if not os.path.isfile(infile):
            self.log_t("Infile '%s' not found\n" % infile, "error")
            gtk.gdk.threads_enter()
            self.crack_button.set_property("sensitive", True)
            gtk.gdk.threads_leave()
            return
        self.log_t("Getting Channel Configuration on Broadcast Channel...\n")
        bursts = self.get_bursts(infile, "0B")
        timeslots = []
        #find immediate assignments and assigned time slots
        for i in bursts:
            ind = i.find(" 06 3f ")
            if ind > 0:
                ts = int(i[ind+9:ind+12], 16) & 0x7
                ch = int(i[ind+12:ind+15], 16) & 0x10
                if True: #not ch:
                    self.log_t("Found Immediate Assignment, ts %i\n" % (ts), "info")
                    if ts not in timeslots:
                        timeslots += [ts]
                #~ else:
                    #~ self.log_t("Found Immediate Assignment, ts %i " % (ts), "info")
                    #~ self.log_t("channel is hopping :(\n", "error")
        timeslots.sort()
        if len(timeslots) > 0:
            dialog = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL, "Select a timeslot")
            label = gtk.Label("Select the timeslot to decode:")
            dialog.vbox.pack_start(label)
            box = gtk.combo_box_new_text()
            for i in timeslots:
                box.append_text("%i" % i)
            dialog.vbox.pack_start(box)
            box.set_active(0)
            dialog.vbox.show_all()
            gtk.gdk.threads_enter()
            ret = dialog.run()
            dialog.destroy()
            gtk.gdk.threads_leave()
            if ret != gtk.RESPONSE_OK:
                gtk.gdk.threads_enter()
                self.crack_button.set_property("sensitive", True)
                gtk.gdk.threads_leave()
                return
            ts = box.get_active_text()
        else:
            self.log_t("No Immediate Assignment found, sorry!\n\n", "error")            
            gtk.gdk.threads_enter()
            self.crack_button.set_property("sensitive", True)
            gtk.gdk.threads_leave()
            return
        self.log_t("Decoding timeslot %s\n" % ts)
        self.log_t("Trying to find System Information Messages\n")
        frames = self.get_frames(infile, "%sS" % ts)
        #find SI5 messages
        si = []
        cmc = None
        for i in frames:
            (fn, hex, frame) = i
            if hex:
                if hex[15:].startswith("06 1d "):
                    self.log_t("Found System Information Type 5, fn %s\n" % fn, "info")
                    if hex[4] != "0":
                        #set TA to 0
                        hex = hex[:4] + "0" + hex[5:]
                        cmd = "%s \"%s\" 2> /dev/null" % (self.utils["gsmframecoder"], hex)
                        with os.popen(cmd) as pipe:
                            new_frames = pipe.read()
                        new_frame = [ x for x in new_frames.split("\n") if x.startswith("1") or x.startswith("0") ]
                        for j in xrange(4):
                            (a, b, c) = frame[j]
                            frame[j] = (a, b, new_frame[j])
                    si += [(fn, hex, frame)]
                #elif hex[15:].startswith("06 1e "):
                #    self.log_t("Found System Information Type 6, fn %s\n" % fn, "info")
                #    si += [i]
                elif hex[9:].startswith("06 35 ") and cmc == None:
                    if hex[16] != "1":
                        self.log_t("Found Ciphering Mode Command, fn %s" % fn, "info")
                        self.log_t("is not A5/1 and ciphering start :(\n", "error")
                    else:
                        self.log_t("Found Ciphering Mode Command, fn %s\n" % fn, "info")
                        cmc = int(fn)
                        break
        if cmc == None:
            self.log_t("No Ciphering Mode Command found, sorry!\n\n", "error")
            gtk.gdk.threads_enter()
            self.crack_button.set_property("sensitive", True)
            gtk.gdk.threads_leave()
            return
        clear_cipher = []
        if len(si) > 0:
            self.log_t("Trying to find suitable Ciphertext\n")
            for i in si:
                (fn, hex, frame) = i
                #sfn = int(fn) + 102 + 102
                #if sfn > cmc:
                    
                for j in frames:
                    (fn2, hex2, frame2) = j
                    if hex2:
                        continue
                    for k in frame2:
                        (fn3, mfn, burst) = k
                        #if int(fn3) == sfn:
                        if (int(fn3) - int(fn)) % 102 == 0 and cmc < int(fn3):
                            self.log_t("Found suitable Ciphertext, fn %s\n" % fn3, "info")
                            clear_cipher += [(frame, frame2, int(fn), int(fn3))]
        else:
            self.log_t("No System Information, sorry!\n\n", "error")
        key = None
        if len(clear_cipher) > 0:
            self.log_t("Trying to find key via kraken\n")
            kc = None
            for i in clear_cipher:
                (clear, cipher, fn1, fn2) = i
                self.log_t("Testing SI, fn:%d with cipher text fn:%d\n" % (fn1, fn2), "info")
                for j in xrange(4):
                    (clfn, mclfn, clburst) = clear[j]
                    (cifn, mcifn, ciburst) = cipher[j]
                    stream = self.xor(clburst, ciburst)
                    try:
                        key = self.send_to_kraken(stream)
                    except Exception, e:
                        self.log_t("Error sending to kraken: %s\n" % str(e), "error")
                    if key != None:
                        self.log_t("Found key '%s' for fn %s\n" % (key, cifn), "info")
                        mfn = mcifn
                        if j == 3:
                            (clfn, mclfn, clburst) = clear[0]
                            (cifn, mcifn, ciburst) = cipher[0]
                        else:
                            (clfn, mclfn, clburst) = clear[j+1]
                            (cifn, mcifn, ciburst) = cipher[j+1]
                        mfn2 = mcifn
                        xor = self.xor(clburst, ciburst)
                                                
                        (key2, pos) = key
                        self.log_t("Trying to find KC...")
                        cmd = "%s %s %s %s %s %s" % (self.utils["find_kc"], key2, pos, mfn, mfn2, xor)
                        with os.popen(cmd) as pipe:
                            tmp = pipe.read().split("\n")
                            for i in tmp:
                                if i.find("*** MATCHED ***") > 0:
                                    kc = " ".join(i.split(" ")[1:9])
                                    self.log_t(" ...found! '%s'\n" % kc, "sucess")
                                    gtk.gdk.threads_enter()
                                    self.decode_key_entry.set_text(kc)
                                    self.decode_infile_entry.set_text(infile)
                                    self.crack_button.set_property("sensitive", True)
                                    gtk.gdk.threads_leave()
                                    return
                        self.log_t(" ...not found, sorry!\n")
            if kc == None:
                self.log_t("Thats it, no more SI to try\n\n", "error")
        else:
            self.log_t("No suitable Ciphertext found!\n", "error")
            #self.log_t("No key found, sorry!\n\n", "error")
        
        gtk.gdk.threads_enter()
        self.crack_button.set_property("sensitive", True)
        gtk.gdk.threads_leave()
    
    def on_decode_button_clicked(self, widget, data=None):
        self.decode_thread = threading.Thread(target=self.decode)
        self.decode_button.set_property("sensitive", False)
        self.decode_thread.start()
        
    def decode(self):
        infile = os.path.expanduser(self.decode_infile_entry.get_text())
        key = self.decode_key_entry.get_text()
        outfile = os.path.expanduser(self.decode_outfile_entry.get_text())
        if not os.path.isfile(infile):
            self.log_t("Infile '%s' not found\n" % infile, "error")
            gtk.gdk.threads_enter()
            self.decode_button.set_property("sensitive", True)
            gtk.gdk.threads_leave()
            return
        self.log_t("Getting Channel Configuration on Control Channel...\n")
        frames = self.get_frames(infile, "1S", key=key)
        ts = None
        #find assignments command and assigned time slots
        for i in frames:
            (fn, hex, frame) = i
            if hex:
                if hex[9:].startswith("06 2e "):
                    ts = int(hex[15:17], 16) & 0x7
                    self.log_t("Found Assignment Command, ts %i\n" % (ts), "info")
                    break
        if not ts:
            self.log_t("No Assignment Command found, sorry!\n", "error")
            gtk.gdk.threads_enter()
            self.decode_button.set_property("sensitive", True)
            gtk.gdk.threads_leave()
            return
        self.log_t("Decoding timeslot %s\n" % ts)
        self.get_bursts(infile, "%dT" % ts, key)
        shutil.move("%s/speech.au.gsm" % os.path.dirname(self.utils["gsm_receive"]), "%s.gsm" % outfile)
        os.popen("%s -d %s.gsm" % (self.utils["toast"], outfile))
        self.log_t("Output has been written to %s\n" % outfile)
        gtk.gdk.threads_enter()
        self.decode_button.set_property("sensitive", True)
        gtk.gdk.threads_leave()
        
    def send_to_kraken(self, stream):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.kraken["host"], int(self.kraken["port"])))
        s.send("crack %s\n" % stream)
        rcv = "Cracking"
        while rcv.startswith("Cracking"):
            rcv = s.recv(4096)
            self.log_t("Kraken: %s" % rcv, "info")
        s.close()
        if rcv.startswith("Found"):
            return (rcv.split(" ")[1], rcv.split(" ")[3])
        return None
    
    def xor(self, in1, in2):
        if len(in1) != len(in2) != 114:
            return ""
        r = ""
        for i in range(114):
            a = ord(in1[i])
            b = ord(in2[i])
            r = r+chr(48^a^b)
        return r
    
    def get_bursts(self, file, channel, key='"00 00 00 00 00 00 00 00"', split='\n'):
        if not os.path.isfile(self.utils["gsm_receive"]):
            self.log("Path to gsm_receive.py not set\n", "error")
            return None
        (source,) = self.source_combobox.get_model()[self.source_combobox.get_active()]
        if source == "USRP":
            #decim = 111.36 for old usrp records
            decim = 111.36
            #decim = 174
            cmd = "cd %s && ./%s -d %f -I %s -c %s -k \"%s\" 2> /dev/null" % (os.path.dirname(self.utils["gsm_receive"]), os.path.basename(self.utils["gsm_receive"]), decim, file, channel, key)
        elif source == "RTLSDR":
            cmd = "cd %s && ./%s -d %f -I %s -c %s -k \"%s\" 2> /dev/null" % (os.path.dirname(self.utils["gsm_receive"]), os.path.basename(self.utils["gsm_receive"]), 35.5555555556, file, channel, key)
        else:
            return []
        with os.popen(cmd) as pipe:
            burst_list = pipe.read().split(split)
        return burst_list
    
    def get_frames(self, file, channel, key='"00 00 00 00 00 00 00 00"'):
        frames = []
        bursts = self.get_bursts(file, channel, key, "C1 ")
        bursts.pop(0)
        for i in bursts:
            tmp = i.split('\n')
            tmp2 = tmp.pop(0).split(': ')
            fn = int(tmp2[0].split(' ')[0])
            mfn = int(tmp2[0].split(' ')[1]) 
            frame = [(fn, mfn, tmp2[1])]
            hex = None
            hex_fn = 0
            for j in tmp:
                if j.startswith("C0"):
                    if len(frame) == 4:
                        break
                    tmp2 = j.split(': ')
                    fn = int(tmp2[0].split(' ')[1])
                    mfn = int(tmp2[0].split(' ')[2])
                    frame += [(fn, mfn, tmp2[1])]
                elif j.startswith("P1") or j.startswith("S1") or j.startswith("P0") or j.startswith("S0"):
                    pass
                else:
                    sp = j.split(": ")
                    if len(sp) > 1:
                        hex = sp[1]
                        hex_fn = sp[0].split(" ")[0]
                        if len(frame) == 4:
                            break
            if len(frame) == 4:
                frames += [(hex_fn, hex, frame)]
        return frames
    
    def on_scan_button_clicked(self, widget, data=None):
        self.scan_window.show_all()
    
    def on_scan_togglebutton_toggled(self, widget, data=None):
        if not widget.get_active():
            self.scan_thread_running = False
            if self.scan_thread != None:
                if self.scan_thread.isAlive():
                    self.scan_thread.join()
        else:
            self.scan_thread_running = True
            self.scan_thread = threading.Thread(target=self.scan)
            self.scan_thread.start()
    
    def scan(self):
        (name, offset, start, diff, arfcn_min, arfcn_max) = self.scan_band_combobox.get_model()[self.scan_band_combobox.get_active()]
        outfile = tempfile.mktemp(prefix="pytacle_scan_", dir=self.dirs["tmp"])
        for arfcn in xrange(arfcn_min, arfcn_max):
            gtk.gdk.threads_enter()
            self.scan_arfcn_label.set_text("Scaning ARFCN %d\n%d left" % (arfcn, arfcn_max - arfcn))
            gtk.gdk.threads_leave()
            freq = (start + (arfcn - offset) * 200 + diff) * 1000
            if not self.scan_thread_running:
                return
            (source,) = self.scan_source_combobox.get_model()[self.scan_source_combobox.get_active()]
            if source == "USRP":
                cmd = [self.utils["python"], self.utils["gsm_receive_usrp"], "-f", str(freq), "-k", "\"00 00 00 00 00 00 00 00\"", "-o", outfile]
                proc = subprocess.Popen(cmd, cwd=os.path.dirname(self.utils["gsm_receive_usrp"]))
            elif source == "RTLSDR":
                cmd = [self.utils["python"], self.utils["gsm_receive_rtl"], "-f", str(freq), "-k", "\"00 00 00 00 00 00 00 00\"", "-o", outfile]
                proc = subprocess.Popen(cmd, cwd=os.path.dirname(self.utils["gsm_receive_rtl"]))
            else:
                return
            time.sleep(4)
            proc.kill()
            bursts = self.get_bursts(outfile, "0B")
            if bursts != None:
                for i in bursts:
                    ind = i.find(" 49 06 1b ")
                    if ind > 0:
                        i = i.split(":")[1]
                        ci = int((i[10:12] + i[13:15]), 16)
                        mcc = int(i[16:17]) * 10 + int(i[17:18]) + int(i[20:21]) * 100
                        mnc = int(i[22:23]) + int(i[23:24]) * 10
                        lac = int((i[25:27] + i[28:30]), 16)
                        try:
                            mcc_string = codes[mcc]["name"]
                        except:
                            mcc_string = "Unknown"
                        try:
                            mnc_string = codes[mcc]["mnc"][mnc]
                        except:
                            mnc_string = "Unknown"
                        gtk.gdk.threads_enter()
                        self.scan_textbuffer.insert_with_tags_by_name(self.scan_textbuffer.get_end_iter(), "Found cell! ARFCN: %d CI: %d MCC: %d (%s) MNC: %d (%s) LAC: %d\n" % (arfcn, ci, mcc, mcc_string, mnc, mnc_string, lac))
                        gtk.gdk.threads_leave()
                        break
        self.scan_thread = None
        os.remove(outfile)
        gtk.gdk.threads_enter()
        self.scan_togglebutton.set_active(False)
        gtk.gdk.threads_leave()
    
def main():
    app = pytacle()
    signal.signal(signal.SIGINT, app.destroy_event)
    try:
        app.main()
    except Exception, e:
        print e
        if DEBUG:
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60

if __name__ == '__main__':
    main()

