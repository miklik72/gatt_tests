#!/usr/bin/env python3


import gatt                             #https://github.com/getsenic/gatt-python
import struct
import datetime
import re
import pprint
from functools import cmp_to_key
from argparse import ArgumentParser

_PIN_STRUCT = '<I'
_DATETIME_STRUCT = '<BBBBB'
_FLAGS_STRUCT = '<BBB'
_TEMPERATURES_STRUCT = '<bbbbbbb'
_LCD_TIMER_STRUCT = '<BB'
_DAY_STRUCT = '<BBBBBBBB'
_HOLIDAY_STRUCT = '<BBBBBBBBb'

def _decode_battery(value):
    value = ord(value)
    if value == 255:
        return None
    return value

def _decode_datetime(value):
    mi, ho, da, mo, ye = struct.unpack(_DATETIME_STRUCT, value)
    return datetime.datetime(
            year=ye + 2000,
            month=mo,
            day=da,
            hour=ho,
            minute=mi)
            
def _decode_flags(value):
    f1, f2, f3 = struct.unpack(_FLAGS_STRUCT, value)
    return '%s %s %s' % tuple(map(bin, (f1, f2, f3)))


def _decode_temperatures(value):
    cur_temp, manual_temp, target_low, target_high, offset_temp, \
            window_open_detect, window_open_minutes = struct.unpack(
                    _TEMPERATURES_STRUCT, value)
    return {
        'current_temp': cur_temp / 2.0,
        'manual_temp': manual_temp / 2.0,
        'target_temp_l': target_low / 2.0,
        'target_temp_h': target_high / 2.0,
        'offset_temp': offset_temp / 2.0,
        'window_open_detection': window_open_detect,
        'window_open_minutes': window_open_minutes,
}

def _decode_lcd_timer(value):
    preload, current = struct.unpack(_LCD_TIMER_STRUCT, value)
    return {
        'preload': preload,
        'current': current,
}

def _day_period_cmp(p1, p2):
    if p1['start'] is None:
        return 1
    if p2['start'] is None:
        return -1
    #return cmp(p1['start'], p2['start']) obsolete function cmp
    return (p1['start'] > p2['start']) - (p1['start'] < p2['start'])

def _decode_day(value):
    max_raw_time = ((23 * 60) + 59) / 10

    raw_time_values = list(struct.unpack(_DAY_STRUCT, value))
    day = []
    #print("BP maxrawt",max_raw_time)
    while raw_time_values:
        raw_start = raw_time_values.pop(0)
        raw_end = raw_time_values.pop(0)
        #print("raws",raw_start,"rawe",raw_end, "rs_modulo",(raw_start * 10) % 60)
        if raw_end > max_raw_time:
            start = None
            end = None
        else:
            if raw_start > max_raw_time:
                start = datetime.time()
            else:
                raw_start *= 10
                start = datetime.time(hour=int(raw_start / 60), minute=int(raw_start % 60))              
            if raw_end > max_raw_time:
                end = datetime.time(23, 59, 59)
            else:
                raw_end *= 10
                end = datetime.time(hour=int(raw_end / 60), minute=int(raw_end % 60))
                        
        if start == end:
            day.append({
                'start': None,
                'end': None,
            })
        else:
            day.append({
                'start': start,
                'end': end,
            })
        #print("BP start end", start, end)

    day.sort(key=cmp_to_key(_day_period_cmp)) #workaround for py3    
    return day

def _decode_holiday(value):
    ho_start, da_start, mo_start, ye_start, \
            ho_end, da_end, mo_end, ye_end, \
            temp = struct.unpack(_HOLIDAY_STRUCT, value)

    if (ho_start > 23) or (ho_end > 23) \
            or (da_start > 31) or (da_end > 31) \
            or (da_start < 1) or (da_end < 1) \
            or (mo_start > 12) or (mo_end > 12) \
            or (mo_start < 1) or (mo_end < 1) \
            or (ye_start > 99) or (ye_end > 99) \
            or (temp == -128):
        start = None
        end = None
        temp = None
    else:
        start = datetime.datetime(
                year=ye_start + 2000,
                month=mo_start,
                day=da_start,
                hour=ho_start)
        end = datetime.datetime(
                year=ye_end + 2000,
                month=mo_end,
                day=da_end,
                hour=ho_end)
        temp = temp / 2.0

    return {
        'start': start,
        'end': end,
        'temp': temp,
}



class CBDevice(gatt.Device):

    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected" % (self.mac_address))

    def services_resolved(self):
        super().services_resolved()

        print("[%s] Resolved services" % (self.mac_address))
        for service in self.services:
            #print("[%s]  Service [%s]" % (self.mac_address, service.uuid))
                        
            for characteristic in service.characteristics:
                #print("[%s]    Characteristic [%s]" % (self.mac_address, characteristic.uuid))
                if service.uuid == "47e9ee00-47e9-11e4-8939-164230d1df67" and characteristic.uuid == "47e9ee30-47e9-11e4-8939-164230d1df67":
                  characteristic.write_value(b'\x00\x00\x00')
                else:
                  characteristic.read_value()

    def characteristic_value_updated(self, characteristic, value):
        print("uuid:", characteristic.uuid, end=' ')
        if characteristic.uuid == "47e9ee2c-47e9-11e4-8939-164230d1df67":
            print("Battery:", _decode_battery(value),"%")
        elif characteristic.uuid == "47e9ee01-47e9-11e4-8939-164230d1df67":
            print("Date&Time:", _decode_datetime(value))
        elif characteristic.uuid == "47e9ee2a-47e9-11e4-8939-164230d1df67":
            print("Flags:", _decode_flags(value))          
        elif characteristic.uuid == "47e9ee2b-47e9-11e4-8939-164230d1df67":
            print("Temperatures")
            for entname, entval in _decode_temperatures(value).items():
               print(entname, entval)
        elif characteristic.uuid == "47e9ee2e-47e9-11e4-8939-164230d1df67":
            print("LCD timer:", _decode_lcd_timer(value))
        elif characteristic.uuid == "47e9ee2d-47e9-11e4-8939-164230d1df67":
            print("fw revision II: {}".format(value.decode()))
        elif re.match(r"47e9ee1\d-47e9-11e4-8939-164230d1df67", characteristic.uuid):
            daynum = characteristic.uuid[7]
            print("DAY",daynum,":", end="")
            for period in _decode_day(value):
                print(period['start'],"-",period['end']," ",sep="",end="") 
            print("")
        elif re.match(r"47e9ee2\d-47e9-11e4-8939-164230d1df67", characteristic.uuid):
            holnum = characteristic.uuid[7]
            print("HOLIDAY",holnum,":", _decode_holiday(value))                                                                            
        elif characteristic.uuid == "00002a05-0000-1000-8000-00805f9b34fb":
            print("service changed: start 0x{:04x} end 0x{:04x}".format((value[1] << 8) + value[0], (value[3] << 8) + value[2]))
        elif characteristic.uuid == "00002a24-0000-1000-8000-00805f9b34fb":
            print("model: {}".format(value.decode()))
        elif characteristic.uuid == "00002a26-0000-1000-8000-00805f9b34fb":
            print("fw revision: {}".format(value.decode()))
        elif characteristic.uuid == "00002a28-0000-1000-8000-00805f9b34fb":
            print("sw revision: {}".format(value.decode()))
        elif characteristic.uuid == "00002a29-0000-1000-8000-00805f9b34fb":
            print("manufacturer: {}".format(value.decode()))            
        else:
            print("RAW:", str(value))
          
arg_parser = ArgumentParser(description="GATT Read Firmware Version Demo")
arg_parser.add_argument('mac_address', help="MAC address of device to connect")
args = arg_parser.parse_args()
                                                                                                               
manager = gatt.DeviceManager(adapter_name='hci0')

device = CBDevice(manager=manager, mac_address=args.mac_address)
device.connect()

manager.run()

