# banner.py
# $Rev$
# Copyright (c) 2014 Able Systems Limited. All rights reserved.
'''This simple code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

This is an example of how a script can be written that uses a python graphics
library (in this case Pillow - see http://pillow.readthedocs.org/index.html)
to draw a banner using v. large text.  It examples the creation and manipulation
of an image, converting it to a format used by the printer and sending the image
to the printer.

Copyright (c) 2014, Able Systems Ltd. All rights reserved.
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

from PIL import Image, ImageFont, ImageDraw


#import struct
MAX_PRINTER_DOTS_PER_LINE = 384
LOGGER = logging.getLogger('banner.py')

# USB specific constant definitions
PIPSTA_USB_VENDOR_ID = 0x0483
PIPSTA_USB_PRODUCT_ID = 0xA053

# Printer commands
SET_FONT_MODE_3 = b'\x1b!\x03'
SET_LED_MODE = b'\x1bX\x2d'
FEED_PAST_TEARBAR = b'\n' * 5
SELECT_SDL_GRAPHICS = b'\x1b*\x08'
SET_DARKNESS_LIGHT = b'\x1bX\x42\x50'
RESTORE_DARKNESS = b'\x1bX\x42\x55'

DOTS_PER_LINE = 384
BYTES_PER_DOT_LINE = DOTS_PER_LINE / 8
USB_BUSY = 66
DEFAULT_FONT = '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'

def setup_logging():
    '''Sets up logging for the application.'''
    LOGGER.setLevel(logging.INFO)

    file_handler = logging.FileHandler('mylog.txt')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(message)s',
                                                datefmt='%d/%m/%Y %H:%M:%S'))

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)

    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(stream_handler)


def setup_usb():
    '''Connects to the 1st Pipsta found on the USB bus'''
    # Find the Pipsta's specific Vendor ID and Product ID (also known as vid
    # and pid)
    dev = usb.core.find(idVendor=PIPSTA_USB_VENDOR_ID,
                        idProduct=PIPSTA_USB_PRODUCT_ID)
    if dev is None:                 # if no such device is connected...
        raise IOError('Printer not found')  # ...report error

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


def convert_image(image):
    '''Takes the bitmap and converts it to a bitarray'''
    imagebits = bitarray(image.getdata(), endian='big')
    LOGGER.info("Done decoding!")
    # pylint: disable=E1101
    return imagebits.tobytes()


def print_image(device, ep_out, data):
    '''Reads the bitarray data and send it (block-by-block) to the
    printer.
    '''
    LOGGER.debug('Start print')
    try:
        ep_out.write(SET_DARKNESS_LIGHT)
        ep_out.write(SET_FONT_MODE_3)
        cmd = struct.pack('3s2B', SELECT_SDL_GRAPHICS,
                      (DOTS_PER_LINE / 8) & 0xFF,
                      (DOTS_PER_LINE / 8) / 256)
        # Arbitrary command length, set to minimum acceptable 24x8 dots
        # this figure should give mm of print
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
                LOGGER.debug('End print')
    finally:
        ep_out.write(RESTORE_DARKNESS)

def parse_arguments():
    '''Parse the arguments passed to the script looking for a font file name
    and a text string to print.  If either are missing defaults are used.
    '''
    txt = 'My First Pipsta Banner!'
    parser = argparse.ArgumentParser()
    parser.add_argument('text', help='the banner text to print',
                        nargs='?', default=txt)
    parser.add_argument('font', type=argparse.FileType('r'),
                        help='a truetype font file', nargs='?',
                        default=DEFAULT_FONT)
    return parser.parse_args()

def get_best_fit_font(font_file_name, text_to_print):
    '''Detemines the largest font that will fit by checking the resultant
    size of the image created for the text, font parameters supplied.
    This assumes a loosely linear relationship between font size selected
    and resultant image size. Note that many fonts include whitespace and
    that this may introduce sub-optimal font sizes as a consequence. 
    Future versions of this script could take this into account to give
    true best fit. 
    '''
    arbitrary_but_large = 5000
    font_sz = arbitrary_but_large
    font = ImageFont.truetype(font_file_name, font_sz)
    image_sz = font.getsize(text_to_print)[1]

    font_sz = (arbitrary_but_large * (MAX_PRINTER_DOTS_PER_LINE*1000)/image_sz) // 1000
    print(font_sz, image_sz)
    return ImageFont.truetype(font_file_name, font_sz)

def main():        
    '''This is the main loop where arguments are parsed, fonts are loaded,
    connections are established, images are processed and the result is
    printed out.
    '''

    # This script is written using the PIL which requires Python 2
    if sys.version_info[0] != 2:
        sys.exit('This application requires python 2.')

    if platform.system() != 'Linux':
        sys.exit('This script has only been written for Linux')
        
    args = parse_arguments()
    setup_logging()
    __send_to_printer(args.font.name, args.text)

def send_to_printer(text):
    '''This is the API call made by the nfc_server to perform a banner print'''
    __send_to_printer(DEFAULT_FONT, text)

def __send_to_printer(font_name, text):
    '''In here printer connections are established, fonts are loaded,
    images are processed and the result is printed out.'''
    usb_out, device = setup_usb()
    usb_out.write(SET_LED_MODE + b'\x01')
    font = get_best_fit_font(font_name, text)
    
    (image_width, __unused) = font.getsize(text)

    # Create an image using the selected font and text.  Mode 1 is -
    #
    #     1-bit pixels, black and white, stored with one pixel per byte
    #
    # (see http://effbot.org/imagingbook/concepts.htm#mode)

	# Draw the image onto an image whose width is that of the paper roll
    image = Image.new('1', (image_width, DOTS_PER_LINE))
    draw = ImageDraw.Draw(image)
    offset = font.getoffset(text)
    draw.text((-offset[0], -offset[1]), text, font=font, fill=1)
    # Rotate the image to be oriented along the length of the paper
    # with the left-most character being printed first
    banner = image.transpose(Image.ROTATE_270)
    # Enable the following line if you want to stash/review the image 
    #image.save("temp.png")

    try:
        print_data = convert_image(banner)
        usb_out.write(SET_LED_MODE + b'\x00')
        print_image(device, usb_out, print_data)
        usb_out.write(FEED_PAST_TEARBAR)
    finally:
        # Ensure the LED is not in test mode
        usb_out.write(SET_LED_MODE + b'\x00')
        
if __name__ == '__main__':
    main()
