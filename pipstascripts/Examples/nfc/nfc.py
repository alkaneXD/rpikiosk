# ModMyPi.py
# $Rev$
# Copyright (c) 2014 Able Systems Limited. All rights reserved.
'''Based on WebPrintMany.  This example has been especially created
for an NFC demo.  The software enacts an operation based on the 
credentials stored on the Pipsta.

Copyright (c) 2014, Able Systems Ltd. All rights reserved.
'''

import argparse
import platform
import signal
import sys
import time
import struct
import re
import pipsta

from usb.core import USBError
import usb.backend.libusb0 as libusb0
import usb.core
import usb.util

class Ascii:
    ESC = 0x1b
    GS  = 0x1d
    ACK = 0x06
    NAK = 0x15
    X = 'X'.encode(encoding='ascii')
    I = 'I'.encode(encoding='ascii')
    A = 'A'.encode(encoding='ascii')
    u = 'u'.encode(encoding='ascii')
    v = 'v'.encode(encoding='ascii')

# Query for printer serial number
QUERY_SERIAL_NUMBER = b'\x1dI\x06' # GS,'I',6
QUERY_CREDENTIALS = b'\x1dI\x7e' # GS,'I',126
FEED_PAST_CUTTER = b'\n' * 5

# USB specific constant definitions
PIPSTA_USB_VENDOR_ID = 0x0483
PIPSTA_USB_PRODUCT_ID = 0xA053

PRINTER_SERIAL_NUMBER_MAX_LENGTH = 10
PRINTER_CREDENTIALS_MAX_LENGTH = 1024
PRINT_JOB_POLL_PERIOD = 3

def parse_arguments():
    '''This scripts expects no arguments, offers help text and that is all.'''
    parser = argparse.ArgumentParser(description='Polls the print server')
    return parser.parse_args()

class PipstaPrinter():

    def __init__(self):
        self.ep_in = None
        self.ep_out = None
        
    def purge_usb_input(self):
        '''Removes any data from the usb input that may be left over from a
        previous connection.
        '''
        while True:
            try:
                dummy = self.ep_in.read(1)
            except USBError as dummy:
                break

    def connect(self):
        '''Establishes a read/write connection to the 1st Pipsta found on the USB
        bus.
        '''

        # Find the Pipsta's specific Vendor ID and Product ID (also known as vid
        # and pid)
        dev = usb.core.find(idVendor=PIPSTA_USB_VENDOR_ID,
                            idProduct=PIPSTA_USB_PRODUCT_ID,
                            backend=libusb0.get_backend())
        if dev is None:                 # if no such device is connected...
            raise IOError('Printer not found')  # ...report error

        try:
            if platform.system() == 'Linux':
                dev.reset()

            # Initialisation. Passing no arguments sets the configuration to the
            # currently active configuration.
            dev.set_configuration()
        except usb.core.USBError as ex:
            raise IOError('Failed to configure the printer', ex)
        except AttributeError as ex:
            raise IOError('Failed to configure the printer')

        cfg = dev.get_active_configuration()  # Get a handle to the active interface

        interface_number = cfg[(0, 0)].bInterfaceNumber
        usb.util.claim_interface(dev, interface_number)
        alternate_setting = usb.control.get_interface(dev, interface_number)
        intf = usb.util.find_descriptor(
            cfg, bInterfaceNumber=interface_number,
            bAlternateSetting=alternate_setting)

        self.ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_OUT
        )

        self.ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_IN
        )

    def get_serial_number(self):
        '''Requests the printer ID from the printer and then returns the
        serial number with any white space stripped from the start/end of the
        string.
        '''
        self.ep_out.write(QUERY_SERIAL_NUMBER)
        return ''.join([chr(x) for
                        x in self.ep_in.read(PRINTER_SERIAL_NUMBER_MAX_LENGTH)]).strip()

    def get_credentials(self):
        '''Requests the NFC credentials from the printer and then returns the
        credentials.  If no credentials are loaded on the printer then a None
        is returned.
        '''
        result = None

        try:
            self.ep_out.write(QUERY_CREDENTIALS)
            result = self.ep_in.read(PRINTER_CREDENTIALS_MAX_LENGTH)
        except usb.core.USBError as unused:
            pass
        except AttributeError as unused:
            pass

        if not result or result[0] == '\0':
            return None

        r = re.compile(r""" 
                       (\w+) 
                       \s*=\s*( 
                       "(?:[^"]*)" 
                       | 
                       [^,]+ 
                       ) 
                       """, re.VERBOSE) 
        results = [ 
            (m.group(1), m.group(2).strip('"')) 
            for m in r.finditer(''.join([chr(x) for x in result]).strip()) 
        ] 
        return dict(results)

    def erase_credentials(self):
        self.ep_out.write(b'\x1bX\x7e\x00')
        
    def get_nfc_settings(self):
        self.ep_out.write(struct.pack('bcb', Ascii.GS, Ascii.I, 125))
        data = self.ep_in.read(1)
        return data[0]
        
    def set_nfc_settings(self, settings):
        cmd = struct.pack('bcbB', Ascii.ESC, Ascii.X, 125, settings)
        self.ep_out.write(cmd)


def process_print_jobs(printer):
    '''Looks up any print jobs for the Pipsta connected and filters the
    jobs by the supplied credentials (if any exist) and finally prints any
    outstanding jobs.
    '''
    credentials = None

    try:
        credentials = printer.get_credentials()
    except USBError as unused:
        #Failed to connect to a printer, abort
        pass
    
    if credentials:
        printer.erase_credentials()
        print(credentials)

        if 'method' in credentials.keys():
            method_name = credentials['method']
            assert method_name.startswith('pipsta.')
            method_name = method_name[7:]

            if method_name in pipsta.__dict__.keys():
                print('Sending job to printer')
                module = pipsta.__dict__[method_name]
                text   = credentials['field']

                if 'send_to_printer' in dir(module):
                    while True:
                        try:
                            module.send_to_printer(text)
                            return
                        except AttributeError as e:
                            print('AttributeError retry - {}'.format(e))
            else:
                print('No recognised API')

def signal_handler(sig_int, frame):
    '''This signal handler negates the need for super user rights when ending
    this application using the 'kill' command.
    '''
    del sig_int, frame
    sys.exit()

def connect_to_printer():
    printer = PipstaPrinter()

    while True:
        try:
            printer.connect()
            printer.set_nfc_settings(0x23)
            return printer
        except IOError as unused:
            pass
        finally:
            pass


def main():
    '''Connect to the printer and the database at regular intervals.  If there
    are any valid print jobs outstanding then print them off.
    '''
    if platform.system() != 'Linux':
        sys.exit('This script has only been written for Linux')
    
    parse_arguments()
        
    signal.signal(signal.SIGINT, signal_handler)

    try:
        process_print_jobs(connect_to_printer())
    except AttributeError as unused:
        pass # A mismatch of libusb seems to have a missing method

    # go to sleep for a while, when awoken check for more work and sleep again
    while True:
        time.sleep(PRINT_JOB_POLL_PERIOD)
        try:
            process_print_jobs(connect_to_printer())
        except AttributeError as unused:
            pass # libusb issue, see above

if __name__ == '__main__':
    main()
