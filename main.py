# Water level with a LoPy
#
# Main script
#
# Author:  J. Barthelemy
# Version: 10 July 2017

import time
import socket
import binascii
import struct
import pycom
import config
from machine import ADC, Pin, deepsleep
from network import LoRa

# setting up the pins to start/stop the sensor
# ... Pin 19 is pulled down and is set to be an output
pin_activation_sensor = Pin('P19', mode=Pin.OUT, pull=Pin.PULL_DOWN)

# setting up the Analog/Digital Converter with 10 bits for the ultrasonic sensor
adc = ADC(bits=10)
# create an analog pin on P20
apin = adc.channel(pin='P20', attn=ADC.ATTN_11DB)

def read_distance():
    '''Reading distance using the ultrasonic sensor'''

    # waking it up
    # ... unlocking the pin
    pin_activation_sensor.hold(False)
    # ... set pin to High for 50 ms
    pin_activation_sensor.value(True)
    time.sleep_us(50)

    # reading 10 values
    list_dist = list()
    for i in range(11):
        list_dist.append(apin() * 5) # Si ADC 12 bits -> 1.25
        time.sleep_us(20000)

    # sorting them
    list_dist.sort()

    # making it asleep by setting the pin to Low and locking its value
    pin_activation_sensor.value(False)
    pin_activation_sensor.hold(True)

    # returning the median distance
    return list_dist[5]

def join_lora():
    '''Joining The Things Network '''

    # init Lorawan
    lora = LoRa(mode=LoRa.LORAWAN, public=1, adr=0, tx_retries=0, device_class=LoRa.CLASS_A)

    # create an OTA authentication params
    app_eui = binascii.unhexlify(config.APP_EUI.replace(' ',''))
    app_key = binascii.unhexlify(config.APP_KEY.replace(' ',''))

    # remove default channels
    for i in range(0, 72):
        lora.remove_channel(i)

    # adding the Australian channels
    for i in range(8, 15):
        lora.add_channel(i, frequency=915200000 + i * 200000, dr_min=0, dr_max=3)
    lora.add_channel(65, frequency=917500000, dr_min=4, dr_max=4)

    for i in range(0, 7):
        lora.add_channel(i, frequency=923300000 + i * 600000, dr_min=0, dr_max=3)

    # join a network using OTAA
    lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)

    # wait until the module has joined the network
    attempt = 0
    while not lora.has_joined() and attempt < config.MAX_JOIN_ATTEMPT:
        time.sleep(2.5)
        attempt = attempt + 1

    if lora.has_joined():
        return True
    else:
        return False

def get_battery_level():
    '''Getting the battery level'''
    # see https://forum.pycom.io/topic/226/lopy-adcs/6

    # read the lopy schematic to see what is the voltage divider applied
    # do not forget to use the proper attenuation
    # then use adc to read the value on pin 16 and depending on the resolution
    # i.e. the number of bits used by the ADC, compute the voltage of the
    # LiPo battery.
    # We might need to test to see what is the voltage of the battery at which
    # it stops to work.

    return 1000

def send_LPP_over_lora(val, bat, port=2):
   '''Sending the water and battery levels over LoraWan on a given port using Cayenne LPP format'''

   # create a LoRa socket
   s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

   # set the LoRaWAN data rate
   s.setsockopt(socket.SOL_LORA, socket.SO_DR, 4)

   # make the socket non blocking
   s.setblocking(False)

   # selecting port
   s.bind(port)

   # creating LPP packets metadata
   # ... distance: channel and data type
   channel_dst = 1
   data_dst    = 2
   # ... battery: channel and data type
   channel_bat = 2
   data_bat    = 2

   # sending the packet
   s.send(bytes([channel_dst, data_dst]) + struct.pack('>h', int(val * 0.1)) +
          bytes([channel_bat, data_bat]) + struct.pack('>h', bat * 10))
   time.sleep_us(250000)

'''
################################################################################
#
# Main script
#
# 1. Read the distance from the sensor
# 2. Read battery value
# 3. Join Lorawan
# 4. Transmit the data if join was successful
# 5. Deepsleep for a given amount of time
#
################################################################################
'''

distance = read_distance()
battery  = get_battery_level()
if join_lora():
    send_LPP_over_lora(distance, battery)
deepsleep(config.INT_SAMPLING)
