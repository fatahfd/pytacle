#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  mcc_mnc.py
#  
#  Copyright 2013 Daniel Mende <mail@c0decafe.de>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

#from http://www.mcc-mnc.com/

codes = {
    402 :   {
        "name"  :   "Netherlands",
        "mnc"   :   {
            2   :   "Tele2",
            4   :   "Vodafone Libertel",
            8   :   "KPN Telecom B.V.",
            12  :   "Telfort",
            15  :   "T-Mobile B.V.",
            16  :   "T-Mobile B.V.",
            20  :   "Orange/T-Mobile",
            21  :   "NS Railinfrabeheer B.V.",
        },
    },
    262 :   {
        "name"  :   "Germany",
        "mnc"   :   {
            1   :   "Telekom/T-mobile",
            2   :   "Vodafone D2",
            3   :   "E-Plus",
            4   :   "Vodafone D2",
            5   :   "E-Plus",
            6   :   "E-Plus",
            7   :   "O2",
            8   :   "O2",
            10  :   "O2",
            11  :   "O2",
            12  :   "O2",
            13  :   "Mobilcom",
            14  :   "Group 3G UMTS",
            16  :   "ViStream",
            17  :   "E-Plus",
        },
    },
    232 :   {
        "name"  :   "Austria",
        "mnc"   :   {
            1   :   "A1 MobilKom",
        },
    },
    802 :   {
        "name"  :   "france",
        "mnc"   :   {
        
        },
    },
}


def _codes2str(mcc, mnc):
    try:
        mcc_string = codes[mcc]["name"]
    except:
        mcc_string = "Unknown"
    try:
        mnc_string = codes[mcc]["mnc"][mnc]
    except:
        mnc_string = "Unknown"
    return "MCC: %d (%s) MNC: %d (%s)" % (mcc, mcc_string, mnc, mnc_string)
