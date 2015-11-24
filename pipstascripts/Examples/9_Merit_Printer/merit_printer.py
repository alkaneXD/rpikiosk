# merit_printer.py
# $Rev$
# Copyright (c) 2015 Able Systems Limited. All rights reserved.
'''This simple code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

This is based on the example '8_Image_Print'.  It loads a base image and
then applies graphics processing to overlay a QR-code encoded message on
to the certificate and to place the pupils name on the certificate.

The files accompanying this script are:

    banknote90a.png - a multicolour base image for the certificate

Copyright (c) 2015, Able Systems Ltd. All rights reserved.
'''

import argparse
import platform
import struct
import sys
import time
import os
import inspect

from bitarray import bitarray
import usb.core
import usb.util

from PIL import Image, ImageDraw, ImageFont, ImageChops
import qrcode

# USB specific constant definitions
PIPSTA_USB_VENDOR_ID = 0x0483
PIPSTA_USB_PRODUCT_ID = 0xA053

# Printer commands
SET_FONT_MODE_3 = b'\x1b!\x03'
SET_LED_MODE = b'\x1bX\x2d'
FEED_PAST_CUTTER = b'\n' * 5
SELECT_SDL_GRAPHICS = b'\x1b*\x08'

# Printer constants
MAX_PRINTER_DOTS_PER_LINE = 384
DOTS_PER_LINE = 384
BYTES_PER_DOT_LINE = DOTS_PER_LINE/8
USB_BUSY = 66

DEFAULT_FONT = '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'

class Pipsta:
    '''Simple class to represent the Pipsta printer.  Wrapping some of
    the printer and USB code in a simple API should result in easier to
    read end developer code.'''
    def __init__(self):
        '''Connects to the 1st Pipsta found on the USB bus'''
        # Find the Pipsta's specific Vendor ID and Product ID (also known as vid
        # and pid)
        self.__device = usb.core.find(idVendor=PIPSTA_USB_VENDOR_ID,
                            idProduct=PIPSTA_USB_PRODUCT_ID)

        # if no such device is connected report error
        if self.__device is None:
            raise IOError('Printer not found')

        try:
            self.__device.reset()

            # Initialisation. Passing no arguments sets the configuration to the
            # currently active configuration.
            self.__device.set_configuration()
        except usb.core.USBError as err:
            raise IOError('Failed to configure the printer', err)

        # Get a handle to the active interface
        cfg = self.__device.get_active_configuration()
        interface_number = cfg[(0, 0)].bInterfaceNumber
        usb.util.claim_interface(self.__device, interface_number)
        alternate_setting = usb.control.get_interface(self.__device,
                                                      interface_number)
        intf = usb.util.find_descriptor(
            cfg, bInterfaceNumber=interface_number,
            bAlternateSetting=alternate_setting)

        self.__bulk_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_OUT
        )

        # check we have a real endpoint handle
        if self.__bulk_out is None:
            raise IOError('Could not find an endpoint to print to')

    def print_image(self, data):
        '''Reads the data and sends it a dot line at once to the printer
        '''
        self.write(SET_FONT_MODE_3)
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
            self.write(b''.join([cmd, data[start:end]]))
        
            res = self.__device.ctrl_transfer(0xC0, 0x0E, 0x020E, 0, 2)
            while res[0] == USB_BUSY:
                time.sleep(0.01)
                res = self.__device.ctrl_transfer(0xC0, 0x0E, 0x020E, 0, 2)

    def write(self, data):
        '''Send the supplied data to the pipsta'''
        self.__bulk_out.write(data)

class BusyLookingPipsta(Pipsta):
    '''We use the test mode of the Pipsta as a simple way of
    communicating to the user that the Raspberry Pi is busy processing
    data for the printer.  This class extends the Pipsta class so that,
    when used in a 'with' statement, the printer shows itself as busy
    (flashes the green LED).

    with PipstaInTestMode(instance_of_pipsta):
        ...

    '''
    def __init__(self):
        Pipsta.__init__(self)
        
    def __enter__(self):
        '''Start the green LEDs flash when a 'with' statement is
        entered'''
        self.write(SET_LED_MODE + b'\x01')

    def __exit__(self, typ, value, traceback):
        '''Stop the green LEDs flash when a 'with' statement is
        exited'''
        self.write(SET_LED_MODE + b'\x00')

def convert_image(image):
    '''Takes the bitmap and converts it to Pipsta image format'''
    imagebits = bitarray(image.getdata(), endian='big')
    imagebits.invert()
    return imagebits.tobytes()

def parse_arguments():
    '''Parse the filename argument passed to the script. If no
    argument is supplied, a default filename is provided.
    '''
    default_pupil = "Joe Bloggs"
    default_msg = "Well done. Good work! Now visit www.pipsta.co.uk"
    parser = argparse.ArgumentParser()
    parser.add_argument('pupil', help='the name of the pupil',
                        nargs='?', default=default_pupil)
    parser.add_argument('msg', help='the message to the pupil',
                        nargs='?', default=default_msg)
    return parser.parse_args()

def prepare_banknote_image():
    '''Produces a scaled and dithered from the supplied banknote
    graphic.'''
    root_dir = os.path.dirname(os.path.abspath(inspect.stack()[-1][1]))
    image = Image.open(os.path.join(root_dir, "banknote90a.png"))
 
    # From http://stackoverflow.com/questions/273946/
    #/how-do-i-resize-an-image-using-pil-and-maintain-its-aspect-ratio
    wpercent = DOTS_PER_LINE / float(image.size[0])
    hsize = int(float(image.size[1]) * float(wpercent))
    image = image.resize((DOTS_PER_LINE, hsize), Image.ANTIALIAS)
    return image.convert('1')

def add_pupils_name(original_image, pupils_name):
    '''Takes the original image and adds the pupils name to the banner
    at the bottom of the image.  Returns the combined image.'''
    font = ImageFont.truetype(DEFAULT_FONT, 30)
    
    # Create an image using the selected font and text.  Mode 1 is -
    #
    #     1-bit pixels, black and white, stored with one pixel per byte
    #
    # (see http://effbot.org/imagingbook/concepts.htm#mode)
    # Draw the image onto an image whose width is that of the paper roll
    original_image_size = original_image.size
    rotated_size = (original_image_size[1], original_image_size[0])
    merit_text = Image.new('1', rotated_size)
    draw = ImageDraw.Draw(merit_text)
    offset = font.getoffset(pupils_name)
    draw.text((-offset[0], -offset[1]), pupils_name, font=font, fill=1)
    x_offset = (original_image_size[1]/2) - (len(pupils_name)*15)/2
    merit_text = ImageChops.offset(merit_text, x_offset, 320)
    
    merit = merit_text.transpose(Image.ROTATE_270)
    return ImageChops.logical_or(merit, original_image)

def add_message(original_image, message):
    '''Converts the supplied message to a QR code and then pasted this
    QR encoded message onto the original image.  Returns the modified
    image.'''
    qr_image = Image.new('1', original_image.size)
    qr_image = qrcode.make(message)
    maxsize = (164, 164)
    qr_image.thumbnail(maxsize, Image.ANTIALIAS)
    qr_image.copy()
    original_image.paste(qr_image, (100, 580, 264, 744))
    return original_image

def main():        
    '''This is the main loop where arguments are parsed, connections
     are established, images are processed and the result is
    printed out.
    '''

    # This script is written using the PIL which requires Python 2
    if sys.version_info[0] != 2:
        sys.exit('This application requires python 2.')

    if platform.system() != 'Linux':
        sys.exit('This script has only been written for Linux')
    
    args = parse_arguments()

    # Connect to the Pipsta
    pipsta = BusyLookingPipsta()
    print_data = None

    # While processing data make the printer look busy (flash its green
    # LED)
    with pipsta:
        merit_image = prepare_banknote_image()
        merit_image = add_pupils_name(merit_image, args.pupil)
        merit_image = add_message(merit_image, args.msg)
        print_data = convert_image(merit_image)

    # Check no errors occured, and print.  This is outside the 'with'
    # statement so any printer errors (indicated by the LEDs) are not
    # masked by the flashing green state.
    if print_data:
        pipsta.print_image(print_data)
        pipsta.write(FEED_PAST_CUTTER)
        
if __name__ == '__main__':
    main()
