#!/usr/bin/env python3

import gatt
import time

class CBDeviceManager(gatt.DeviceManager):
    def device_discovered(self, device):
        print("Discovered [%s] %s" % (device.mac_address, device.alias()))

print("set manager")
manager = CBDeviceManager(adapter_name='hci0')
print("start discovery")
manager.start_discovery()
for i in range(20):
    print ('.', end = '', flush=True)
    time.sleep(1)


print("\nstop discovery")
manager.stop_discovery()
print("print devices")
for device in manager.devices():
  if device.alias() == "Comet Blue":
    print("CB device [%s] %s" % (device.mac_address, device.alias()))
  else:
    print("Other device [%s] %s" % (device.mac_address, device.alias()))
  
  
