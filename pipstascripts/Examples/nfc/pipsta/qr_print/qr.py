# qr.py
# $Rev$
# Copyright (c) 2014 Able Systems Limited. All rights reserved.
'''This simple code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

This example's using a python library to generate a QR-Code and then printing
this code to the PIPSTA connected to the Raspberry-Pi.  This code uses the
Pillow library (see http://pillow.readthedocs.org/index.html).

Copyright (c) 2014 Able Systems Limited. All rights reserved.
'''

import argparse
import logging
import platform
import struct
import sys
import time

from bitarray import bitarray
import usb.core
import usb.util

from PIL import Image
import qrcode

MAX_PRINTER_DOTS_PER_LINE = 384
LOGGER = logging.getLogger('qr.py')
SET_FONT_MODE_3 = b'\x1b!\x03'
SET_LED_MODE = b'\x1bX\x2d'
FEED_PAST_TEARBAR = b'\n' * 5
SELECT_SDL_GRAPHICS = b'\x1b*\x08'

# USB specific constant definitions
PIPSTA_USB_VENDOR_ID = 0x0483
PIPSTA_USB_PRODUCT_ID = 0xA053

DOTS_PER_LINE = 384
BYTES_PER_DOT_LINE = DOTS_PER_LINE / 8

USB_BUSY = 66


def parse_arguments():
    '''Parse the command line arguments the script received.'''
    parser = argparse.ArgumentParser()
    parser.add_argument('text', help='the text to encode and print',
                    nargs='?', default='Some example text')
    parser.add_argument('--file', type=argparse.FileType('rb'),
                        help='a file to convert to barcode')
    return parser.parse_args()


def setup_logging():
    '''Configures the logging engine, it outputs logging data to a file
    called 'mylog.txt' and to the terminal.
    '''
    LOGGER.setLevel(logging.INFO)

    file_handler = logging.FileHandler('mylog.txt')
    file_handler.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)

    file_handler.setFormatter(logging.Formatter(
        fmt='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S'))

    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(stream_handler)

def setup_usb():
    '''Find the Pipsta's specific Vendor ID and Product ID (also known as vid
    and pid)
    '''

    dev = usb.core.find(idVendor=PIPSTA_USB_VENDOR_ID,
                        idProduct=PIPSTA_USB_PRODUCT_ID)

    # if no such device is connected report an error
    if dev is None:
        raise IOError('Printer not found')

    try:
        dev.reset()

        # Initialisation. Passing no arguments sets the configuration to the
        # currently active configuration.
        dev.set_configuration()
    except usb.core.USBError as err:
        raise IOError('Failed to configure the printer', err)

    # Get a handle to the active interface
    cfg = dev.get_active_configuration()

    interface_number = cfg[(0, 0)].bInterfaceNumber
    usb.util.claim_interface(dev, interface_number)
    alternate_setting = usb.control.get_interface(dev, interface_number)
    intf = usb.util.find_descriptor(
        cfg, bInterfaceNumber=interface_number,
        bAlternateSetting=alternate_setting)

    ep_out = usb.util.find_descriptor(
        intf,
        custom_match=lambda e:
        usb.util.endpoint_direction(e.bEndpointAddress) ==
        usb.util.ENDPOINT_OUT
    )

    if ep_out is None:  # check we have a real endpoint handle
        raise IOError('Could not find an endpoint to print to')

    return ep_out, dev


def pad_image(image):
    '''Scale image to cover whole width whilst ensuring the aspect ratio is
    maintained.
    '''
    ratio = (384000 / image.size[0])
    # Fill width, at nearest 24 dot height to give closest aspect ratio
    new_size = ((384, ((image.size[1] * ratio) / 1000 // 24) * 24))
    return image.resize(new_size, Image.ANTIALIAS)

def validate_image(image):
    '''Ensures the image dimensions are compatible with the printer.'''
    assert image.size[0] % 8 == 0, 'Width must be divisible by 8.'
    assert image.size[1] % 24 == 0, 'Height must be divisible by 24.'
    assert image.size[0] <= MAX_PRINTER_DOTS_PER_LINE, \
           'QR-Code width exceeds paper width'

def convert_image_to_printer_format(image):
    '''Takes the bitmap and converts it to PIPSTA 24-bit image format'''
    imagebits = bitarray(image.getdata(), endian='big')
    LOGGER.info("Done decoding!")
    # pylint: disable=E1101
    imagebits.invert()
    return imagebits.tobytes()

def print_image(ep_out, device, data):
    '''Sends the prepared printer data to the printer.  If a CR need sending
    inbetween each row then the cr_period is non-zero and is used to
    indicate when to send the CR
    '''
    # Into contiguous graphics mode
    ep_out.write(SET_FONT_MODE_3)
    cmd = struct.pack('3s2B', SELECT_SDL_GRAPHICS,
                      (DOTS_PER_LINE / 8) & 0xFF,
                      (DOTS_PER_LINE / 8) / 256)

    # Arbitrary command length, set to minimum acceptable 24x8 dots this figure
    # should give mm of print
    lines = len(data)//BYTES_PER_DOT_LINE
    start = 0
    
    for line in range (0, lines):    
        start = line * BYTES_PER_DOT_LINE
        # intentionally +1 for slice operation below
        end = start + BYTES_PER_DOT_LINE
        # ...to end (end not included)            
        ep_out.write(b''.join([cmd, data[start:end]]))
        res = device.ctrl_transfer(0xC0, 0x0E, 0x020E, 0, 2)
        while res[0] == USB_BUSY:
            time.sleep(0.01)
            res = device.ctrl_transfer(0xC0, 0x0E, 0x020E, 0, 2)

def main():
    '''The main function of the script.  This creates a QR code and then prints
    the image to the Pipsta printer connected to the Raspberry-Pi.  The script
    accepts a file (-f | --file) if specified.  If no file is specified the user
    will be prompted for some data.
    '''
    
    # This application is written using the PIL which requires Python 2
    if sys.version_info[0] != 2:
        sys.exit('This script requires python 2.')

    if platform.system() != 'Linux':
        sys.exit('This script has only been written for Linux')
    
    args = parse_arguments()
    setup_logging()

    if args.file:
        with args.file:
            data = args.file.read()
    else:
        data = args.text

    send_to_printer([data])

def send_to_printer(data):
    '''Opens a USB connection to the printer, prepares an image of the QRCode
    and sends it to the printer.'''
    print('qr.py - ' + str(data))
    usb_out, device = setup_usb()
    
    try:
        usb_out.write(SET_LED_MODE + b'\x01')
        image = pad_image(qrcode.make(data))
        validate_image(image)
        usb_out.write(SET_LED_MODE + b'\x00')
        print_image(usb_out, device, convert_image_to_printer_format(image))
        usb_out.write(FEED_PAST_TEARBAR)
    except qrcode.exceptions.DataOverflowError as dummy:
        LOGGER.error("Too much data was provided for printing")
    finally:
        usb_out.write(SET_LED_MODE + b'\x00')

if __name__ == '__main__':
    main()
