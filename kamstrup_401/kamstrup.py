#!/usr/bin/python
#
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# <phk@FreeBSD.ORG> wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return.   Poul-Henning Kamp
# ----------------------------------------------------------------------------
#
# Modified for Domotics and single request.
#
# Modified by Frank Reijn and Paul Bonnemaijers for Kamstrup Multical 402
#
# Modified by Sander Gols to integrate in HA component
#
# Modified by B for Kamstrup Multical 401 - e.g. removing all of the other stuff

import serial

import re

import logging

_LOGGER: logging.Logger = logging.getLogger(__package__)

#######################################################################
#

class Kamstrup(object):
    def __init__(self, serial_port, baudrate, timeout):

        self.ser = serial.Serial(port=serial_port, baudrate=baudrate, timeout=timeout)
        
        self.ser.bytesize=serial.SEVENBITS
        self.ser.parity=serial.PARITY_EVEN
        self.ser.stopbits=serial.STOPBITS_TWO
        #self.ser.xonxoff=0
        #self.ser.rtscts=0

    def readMeter(self):
        # Send initialize
        initCommand='/?!\x0D\x0A'
        _LOGGER.debug("Sending initialize %s", str(initCommand.encode('utf-8')))
        self.ser.write(initCommand.encode('utf-8'))
        self.ser.flush()
        
        # Wait for initialize response
        
        # Response details:
        # /[XXX] [Z] MCC [CR] [LF]   /KAM0MCC[CR][LF]
        # XXX is manufacturer string
        # Z is desired baudrate of the meter
        # Z=0: 300Baud
        # Z=1: 600Baud
        # Z=2: 1200Baud
        # Z=3: 2400Baud
        # Z=4: 4800Baud
        # Z=5: 9600Baud
        # Z=6: 19200Baud
        
        responseBuffer = ''
        while '/' not in responseBuffer:
            responseBuffer = str(self.ser.readline(), "utf-8")
            if '/?!\x0D\x0A' in responseBuffer:
                responseBuffer = str(self.ser.readline(), "utf-8")
        initResponse = responseBuffer.strip().split('\r\n')
        
        # Process initialize response
        _LOGGER.debug("Received initialize response: %s", initResponse[0])
        manufacturerFlagID = str(responseBuffer[1:4])
        baudrateIdentifier = str(responseBuffer[4:5])
        if baudrateIdentifier == '0': baudrate = "300"
        elif baudrateIdentifier == '1': baudrate = "600"
        elif baudrateIdentifier == '2': baudrate = "1200"
        elif baudrateIdentifier == '3': baudrate = "2400"
        elif baudrateIdentifier == '4': baudrate = "4800"
        elif baudrateIdentifier == '5': baudrate = "9600"
        elif baudrateIdentifier == '6': baudrate = "19200"
        else: baudrate  = "unknown"
        
        _LOGGER.debug("Manufacturur FLAG ID: %s, preferred baudrate identifier: %s, preferred baudrate: %s (neither of these are used, but logging em anyway ...)", 
            manufacturerFlagID, 
            baudrateIdentifier,
            baudrate,
        )
        
        # Send acknowledge for meter reading mode to receive data
        # [ACK]0[Z][Y] [CR] [LF]
        # Z is the baudrate (baudrate of 300 is fixed, so won't bother to use baudrateIdentifier)
        # Y can be 0 or 1. Value 0 sets the actual meterreading mode, Value 1 sets the programming mode
        ackCommand='\x06000\x0D\x0A'
        _LOGGER.debug("Sending acknowledge %s", str(ackCommand.encode('utf-8')))
        self.ser.write(ackCommand.encode('utf-8'))
        self.ser.flush()
        
        # Wait for acknowledge 
        # Stuff everything we receive into an array and stop when we get \0x03
        responseBuffer = ''
        ackResponse = []
        ackResponseIndex = 0
        ETX = False
        while not ETX:
            responseBuffer = str(self.ser.readline(), "utf-8")            
            if '\x060' in responseBuffer:
                responseBuffer = str(self.ser.readline(), "utf-8")
            if '\x03' in responseBuffer:
                ETX = True
            ackResponse.extend(responseBuffer.strip().split('\r\n'))
            ackResponseIndex = ackResponseIndex + 1
        
        # Process acknowledge response
        ## Example response
        ##\x020.0(00002742640)6.8(0456.631*GJ)6.26(3447.381*m3)6.31(0040345*h)!
        # We already know we want the first array item, so won't bother to loop through the array
        _LOGGER.debug("Received acknowledge response: %s", ackResponse[0])
        # Do some matching without grabbing the silly stuff in front and after the values we want
        heatEnergy = re.search("(?:6\.8\()(.*?)(?:\*GJ\))",ackResponse[0])
        volume = re.search("(?:6\.26\()(.*?)(?:\*m3\))",ackResponse[0])
        hoursCounter = re.search("(?:6\.31\()(.*?)(?:\*h\))",ackResponse[0])
        
        # Store the stuff
        # If the regular expression match returned None, do nothing about it, someone else will handle it, otherwise grab group 1 from the match
        if heatEnergy:
            heatEnergy = float(heatEnergy[1])
            _LOGGER.debug("Heat Energy: %s", str(heatEnergy))
        if volume:
            volume = float(volume[1])
            _LOGGER.debug("Volume: %s", str(volume))
        if hoursCounter:
            hoursCounter = int(hoursCounter[1])
            _LOGGER.debug("Hours Counter: %s", str(hoursCounter))
        
        return (heatEnergy, volume, hoursCounter)
