# Water level with a LoPy
#
# Boot script
#
# Author:  J. Barthelemy
# Version: 04 July 2017

from machine import UART
import pycom
import os
from network import WLAN

# deactivate wifi
wlan = WLAN()
wlan.deinit()

# disabling the heartbeat
pycom.heartbeat(False)

# setting up the communication interface
uart = UART(0, 115200)
os.dupterm(uart)
