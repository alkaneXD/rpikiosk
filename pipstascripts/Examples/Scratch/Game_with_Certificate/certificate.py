# certificate.py
# $Rev$
# Copyright (c) 2014 Able Systems Limited. All rights reserved.
'''This simple code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

Uses a python graphics library (in this case Pillow - see
http://pillow.readthedocs.org/index.html)

This script is intended for use with the NumberQuiz.sb Scratch game.
'''
import argparse
import binascii
import inspect
import logging
import os
import platform
import struct
import sys

from bitarray import bitarray
import usb.control
import usb.core
import usb.util

from PIL import Image, ImageChops
from PIL import ImageDraw
from PIL import ImageFont
import scratch


# USB specific constant definitions
PIPSTA_USB_VENDOR_ID = 0x0483
PIPSTA_USB_PRODUCT_ID = 0xA053

# Printer commands
QUERY_SERIAL_NUMBER = b'\x1dI\x06' # GS,'I',6
SET_TEXT_NORMAL = b'\x1b!\x00'
SET_TEXT_DOUBLE_HEIGHT = b'\x1b!\x10'
SET_TEXT_DOUBLE_WIDTH = b'\x1b!\x20'
SET_TEXT_UNDERLINED = b'\x1b!\x80'
SET_TEXT_DOUBLE_HEIGHT_AND_WIDTH = b'\x1b!\x30'
START_BARCODE_3OF9 = b'\x1dk\x04'
SET_SPOOLING_MODE = b'\x1bL'
UNSET_SPOOLING_MODE = b'\x1dL'
SET_FONT_MODE_3 = b'\x1b!\x03'
SELECT_32BIT_GRAPHICS = b'\x1b*\x20'

MAX_PRINTER_DOTS_PER_LINE = 384

LOGGER = logging.getLogger('certificate.py')

def parse_arguments():
    '''This script expects no arguments, offers help text and that is all.'''
    def_fnt= '/usr/share/fonts/type1/gsfonts/z003034l.pfb'
    parser = argparse.ArgumentParser(description='Instantiates a connection to'
                                     ' scratch. and then awaits instructions'
                                     ' from the scratch environment')
    parser.add_argument('font', type=file, nargs='?',
                        help='Font file for pupils name on the certificate', default=def_fnt)
    return parser.parse_args()

def setup_logging():
    '''Configures the logging engine, it outputs logging data to a file
    called 'mylog.txt' and to the terminal.
    '''
    LOGGER.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler('mylog.txt')
    file_handler.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)

    file_handler.setFormatter(logging.Formatter(
        fmt='%(asctime)s %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S'))

    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(stream_handler)

# The following was adapted from
# http://stackoverflow.com/questions/15857117/python-pil-text-to-image-and-fonts
def pick_font(file_name):
    '''Loads the named font, the font name should not have the file extension.
    so (for example) fontName should be assigned the value "comic_andy".
    '''
    return ImageFont.truetype(file_name, 50)
    
def generate_name(name, font):
    '''Generates an image that consists of the name supplied in the font
    supplied.
    '''
    name_im = new_image(384, 240)
    draw = ImageDraw.Draw(name_im)
    draw.text((15, 15), name, font = font, fill=1)
    draw = ImageDraw.Draw(name_im)
    name_im = trim(name_im)
    #Scale up
    size = name_im.size
    ratio = (384000 / size[0])
    # Fill width, at nearest 24 dot height to give closest aspect ratio
    scaled_size = ((384, ((size[1] * ratio) / 1000 // 24) * 24))
    name_im = name_im.resize(scaled_size, Image.ANTIALIAS)
    name_im = name_im.convert('1')
    LOGGER.info(name + ' image generated!')
    return name_im
    
# The following was adapted from
# http://stackoverflow.com/questions/10615901/trim-whitespace-using-pil
def trim(img):
    '''Trims the image to remove whitespace'''
    background = Image.new(img.mode, img.size, img.getpixel((0, 0)))
    diff = ImageChops.difference(img, background)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        img = img.crop(bbox)

    return img
        
def new_image(width, height):
    '''Creates a new image object for printing the user name to'''
    img = Image.new("RGBA", (width, height), (255, 255, 255))
    img.convert('L')
    return img

def load_image(filename):
    '''Loads an image from the named png file.  Note that the extension must
    be ommitted from the parameter.
    '''
    root_dir = os.path.dirname(os.path.abspath(inspect.stack()[-1][1]))
    return Image.open(os.path.join(root_dir, filename + '.png')).convert('1')

def validate_image(image):
    '''Ensures the image dimensions are compatible with the printer.'''
    assert image.size[0] % 8 == 0, 'Width must be divisible by 8.'
    assert image.size[1] % 24 == 0, 'Height must be divisible by 24.'
    assert image.size[0] <= MAX_PRINTER_DOTS_PER_LINE, \
           'image width exceeds paper width'

def convert_image_to_printer_format(image):
    '''Takes an image and converts the data into something that the Pipsta
    printer recognises.
    '''
    (width, height) = image.size
    area = width * height

    # Convert to bitarray for manipulation
    imagebits = bitarray(image.getdata())
    # required as img has white = true (as RGB all = 255), and we are
    # rendering black dots
    # pylint: disable=E1101
    imagebits.invert()

    printbits = bitarray(area)
    # This loop converts standard image orientation to single dot graphics,
    # populating printbits with imagebits
    LOGGER.debug("Starting decode to print dots (size={})".format(image.size))
    for image_bit_index in range(0, area):
        width_times_byte_height = width << 3
        width_times_bit_height = width_times_byte_height * 3
        print_col = image_bit_index % width
        char_row = image_bit_index // width_times_bit_height
        print_byte = ((image_bit_index % width_times_bit_height) //
                      (width_times_byte_height)) + (3 * print_col)
        print_bit = (image_bit_index % width_times_byte_height) // width
        print_bit_index = print_bit + (print_byte * 8) + \
                          (char_row * width_times_bit_height)
        printbits[print_bit_index] = imagebits[image_bit_index]

    LOGGER.debug("Done decoding!")
    return printbits

def print_image(print_data, cr_period, ep_out):
    '''Sends the prepared printer data to the printer.  If a CR need sending
    inbetween each row then the cr_period is non-zero and is used to
    indicate when to send the CR.
    '''
    # Into contiguous graphics mode, if graphics are too large (causing
    # corruption then remove the ESC,'L' and GS,'L' command pair.
    try:
        send_command(SET_SPOOLING_MODE, ep_out)
        send_command(SET_FONT_MODE_3, ep_out)
        print_bytes = print_data.tobytes()
    
        blocksize = 0xC0 * 6
        n_1 = (blocksize // 0x18) & 0xFF  # number of 24 bit 'strips' to render
        n_2 = (blocksize // 0x18) // 256
        send_cr = False
        
        # Arbitrary command length, set to minimum acceptable 24x8 dots
        for block in range(0, len(print_data) / blocksize):
            # Process width into two byte variables
            cmd = struct.pack('3s2B', SELECT_32BIT_GRAPHICS, n_1, n_2)
            start = (block * blocksize) // 8
            end = ((block + 1) * blocksize) // 8
            
            for byte_index in range(start, end):
                cmd += print_bytes[byte_index]
                if cr_period and byte_index % cr_period == 0:
                    send_cr = True
                else:
                    send_cr = False
                    
            if send_cr == True:
                send_command('\n', ep_out)
                send_cr = False
                
            send_command(cmd, ep_out)
    finally:
        # Exit contiguous mode, see previous ESC,'L'
        send_command(UNSET_SPOOLING_MODE, ep_out)
        
def send_image(image, ep_out):
    '''Performs some sanity checks and then sends the image supplied to the
    printer.
    '''
    validate_image(image)
    (width, height) = image.size
    
    if(width < MAX_PRINTER_DOTS_PER_LINE and height > 24):
        # Limitation of this approach: force Carriage Return for graphics >24
        # dots high after their width. If you wish to use inline graphics (i.e.
        # graphics succeeded by text), create separate 24 dot high graphics for
        # each line. Fire CR after single character line graphics width.
        cr_period = (width * 24 / 8) 
    else:
        cr_period = 0
        
    # This loop converts standard image orientation to single dot graphics,
    # populating printbits with imagebits
    sendable = convert_image_to_printer_format(image)
    
    # Into contiguous graphics mode
    print_image(sendable, cr_period, ep_out)

def listen(scratch_connection):
    '''Polls the scratch connection for a message, when one is received
    then it yields control.  Throws an exception on error.
    '''
    while True:
        try:
            received_data = scratch_connection.receive()
            if received_data[0] == 'broadcast':
                yield received_data[1]
        except scratch.ScratchError:
            raise StopIteration

def centre_justify(msg, double_width):
    '''Produces a text string that is centrally justified'''
    num_of_chars = 16 if double_width else 32
    format_string = '{{:^{}}}'.format(num_of_chars)
    return format_string.format(msg)

def purge_usb_input(usb_in):
    '''Removes any data from the usb input that may be left over from a
    previous connection.
    '''
    while True:
        try:
            dummy = usb_in.read(1)
        except usb.core.USBError as dummy:
            break

def setup_usb():
    '''Connects to the USB bus, searches for an Pipsta (selecting the 1st found)
    then establishes the input andn output endpoints.
    '''
    # Find the Pipsta's specific Vendor ID and Product ID
    dev = usb.core.find(idVendor=PIPSTA_USB_VENDOR_ID,
                        idProduct=PIPSTA_USB_PRODUCT_ID)

    # was it found?
    if dev is None:
        raise ValueError('Device not found')
    
    try:
        dev.reset()
        
          # Initialisation. Passing no arguments sets the configuration to the
          # currently active configuration.
        dev.set_configuration()    
    except usb.core.USBError as dummy:
        raise ValueError('Failed to configure the printer')
    
    # set the active configuration. With no arguments, the first
    # configuration will be the active one
    dev.set_configuration()
    
    # get an endpoint instance
    cfg = dev.get_active_configuration()
    interface_number = cfg[(0, 0)].bInterfaceNumber
    alternate_setting = usb.control.get_interface(dev, interface_number)
    intf = usb.util.find_descriptor(
        cfg, bInterfaceNumber = interface_number,
        bAlternateSetting = alternate_setting
    )
    
    # Get the out Endpoint
    ep_out = usb.util.find_descriptor(
        intf,
        # match the first OUT endpoint
        custom_match = \
        lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_OUT
    )
    ep_in = usb.util.find_descriptor(
        intf,
        # match the first OUT endpoint
        custom_match = \
        lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_IN
    )
    
    assert ep_out is not None
    assert ep_in is not None

    purge_usb_input(ep_in)
    return (ep_out, ep_in)

def read_string_from_printer(ep_in):
    '''A tiny wrapper that returns the printers response as a string.'''
    try:
        data = ep_in.read(15)
        if data != None:
            return ''.join([chr(c) for c in data])
    except usb.core.USBError as dummy:
        pass # Minimal handling of exception
    
    return ''
    
def query_serial_number(ep_out, ep_in):
    '''Using the in and out endpoints on the Pipsta printer, queries the printer
    for its serial number.
    '''
    # GS,I,6 Gets serial number (see Pipsta programmers guide for information)
    send_command(QUERY_SERIAL_NUMBER, ep_out)

    # read the response
    serial_number = read_string_from_printer(ep_in)
    
    if serial_number:
        LOGGER.info('Serial Number is: {}'.format(serial_number))
    else:
        LOGGER.info('No serial #')

def print_text(text, is_centred, is_double_width, ep_out):
    '''Sends plain text to the printer for .. printing'''
    if is_centred:
        text = centre_justify(text, is_double_width)

    LOGGER.info(text)
    ep_out.write(text)

def send_command(cmd, ep_out):
    '''Sends a command to the Pipsta and logs it'''
    ep_out.write(cmd)
    LOGGER.debug(binascii.hexlify(cmd))

class MessageListener:
    '''Handler for all broadcast messages.  If a message looks like an Pipsta
    command then it is handled appropriately.
    '''
    __is_double_width = False
    __is_centre_justified = False
    __name_image = None
    __awaiting_barcode_payload = False
    __awaiting_font_image_payload = False
    __name_font = None
    __printer_out_ep = None
        
    def __init__(self, name_font, printer_out_endpoint):
        '''Initialise all the member variables to sensible defaults.  No
        validation is provided on the name_font (used to render the pupils name
        on the certificate).  The printer_out_endpoint is the first bulk out
        endpoint enumerated on the printer.
        '''
        self.__is_double_width = False
        self.__is_centre_justified = False
        self.__name_image = None
        self.__awaiting_barcode_payload = False
        self.__awaiting_font_image_payload = False
        self.__name_font = name_font
        self.__printer_out_ep = printer_out_endpoint
    

    def start_barcode(self):
        '''Configure the printer to produce a barcode instead of printing text.
        All data received after this point will be used as data for the barcode
        renderer.
        '''
        self.__awaiting_barcode_payload = True
        send_command(START_BARCODE_3OF9, self.__printer_out_ep)


    def double_height_text(self):
        '''Set the Pipsta font mode to double height.  All text after this will
        be printed in this form until the font mode is changed.
        '''
        self.__is_double_width = False
        send_command(SET_TEXT_DOUBLE_HEIGHT, self.__printer_out_ep)

    def double_width_text(self):
        '''Set the Pipsta font mode to double width.  All text after this will
        be printed in this form until the font mode is changed.
        '''
        self.__is_double_width = True
        send_command(SET_TEXT_DOUBLE_WIDTH, self.__printer_out_ep)

    def set_normal_text(self):
        '''Set the Pipsta font mode to normal.  All text after this will be
        printed in this form until the font mode is changed.
        '''
        self.__is_double_width = False
        send_command(SET_TEXT_NORMAL, self.__printer_out_ep)

    def set_underlined_text(self):
        '''Set the Pipsta font mode to underlined.  All text after this will be
        printed in this form until the font mode is changed.
        '''
        self.__is_double_width = False
        send_command(SET_TEXT_UNDERLINED, self.__printer_out_ep)

    def set_double_height_and_width(self):
        '''Set the Pipsta font mode to double height and double width.  All text
        after this will be printed in this form until the font mode is changed.
        '''
        self.__is_double_width = True
        send_command(SET_TEXT_DOUBLE_HEIGHT_AND_WIDTH, self.__printer_out_ep)


    def print_top_flourish(self):
        '''Convert the certificates top flourish to a set of Pipsta graphics
        commands that will render the image and then send the commands to the
        printer.
        '''
        image = load_image('TopFlourish')
        send_image(image, self.__printer_out_ep)


    def print_mid_flourish(self):
        '''Convert the certificates mid flourish to a set of Pipsta graphics
        commands that will render the image and then send the commands to the
        printer.
        '''
        image = load_image('MidFlourish')
        send_image(image, self.__printer_out_ep)


    def print_bottom_flourish(self):
        '''Convert the certificates end flourish to a set of Pipsta graphics
        commands that will render the image and then send the commands to the
        printer.
        '''
        image = load_image('TopFlourish')
        image = image.rotate(180)
        send_image(image, self.__printer_out_ep)


    def print_scratch_image(self):
        '''Produce a set of Pipsta printer graphics commands that will render
        the 'scratch' characters image and then send those commands to the
        printer.
        '''
        image = load_image('scratch')
        send_image(image, self.__printer_out_ep)


    def finish_print_barcode(self, data):
        '''Send the data provided to the Pipsta printer.  The printer is already
        configured to print a barcode using this data.  Append a terminator to
        the message to mark the end of the barcode data.
        '''
        send_command(data, self.__printer_out_ep)
        send_command('\0', self.__printer_out_ep)

        
    def print_pupils_name(self):
        '''The pupils name must have already been received and the image based
        must on the name must have been created.  Send the image to the Pipsta
        using graphics commands.
        '''
        if self.__name_image:
            send_image(self.__name_image, self.__printer_out_ep)
        
    def process_data(self, command):
        '''This is the default method called if the command from scratch is not
        recognised.  It is assumed the payload is actually data and not a
        command.  If the data is expected it will be handled accordingly;
        otherwise it is sent directly to the Pipsta printer.
        '''
        if self.__awaiting_barcode_payload == True:
            self.finish_print_barcode(command)
            self.__awaiting_barcode_payload = False
        elif self.__awaiting_font_image_payload == True:
            self.__name_image = generate_name(command, self.__name_font)
            self.__awaiting_font_image_payload = False
        else:
            print_text(command, self.__is_centre_justified,
                       self.__is_double_width, self.__printer_out_ep)
    
    def send_newline(self):
        '''Convenience function to send a new line to the printer.
        '''
        send_command('\n', self.__printer_out_ep)
        
    def set_text_hcentred(self):
        '''Set a flag to cause any text that follows to be horizontally
        centered.'''
        self.__is_centre_justified = True
    
    @classmethod
    def exit(cls):
        '''Disconnect from scratch and exit. The
        classmethod decorator is used to indicate that there is no use of the
        class instance (pylint error).
        '''
        sys.exit()
        
    def start_printing_pupils_name(self):
        '''Flags that any data received after this point should be considered
        as data.  That data being the pupils name.
        '''
        self.__awaiting_font_image_payload = True

    def run(self, scratch_conn):
        '''This method connects to the scratch environment and processes any
        commands it receives.  If the command is unknown it is sent directly to
        Pipsta printer.
        '''
        
        # A common implementation of switch statements in python is using a
        # dictionary. Here the command_string string is mapped to a function
        # pointer.
        cmd_table = {'cmd_top_flourish' : self.print_top_flourish,
                     'cmd_mid_flourish': self.print_mid_flourish,
                     'cmd_bottom_flourish': self.print_bottom_flourish,
                     'cmd_scratch_image': self.print_scratch_image,
                     'cmd_barcode3of9': self.start_barcode,
                     'cmd_doubleheight': self.double_height_text,
                     'cmd_doublewidth': self.double_width_text,
                     'cmd_normaltext': self.set_normal_text,
                     'cmd_underlined':self.set_underlined_text,
                     'cmd_display_name': self.print_pupils_name,
                     'cmd_newline': self.send_newline,
                     'cmd_doubleheight_and_width'
                     : self.set_double_height_and_width,
                     'cmd_centre_justify': self.set_text_hcentred,
                     'cmd_exit': exit,
                     'cmd_gen_name': self.start_printing_pupils_name}
        
        for command_string in listen(scratch_conn):
            # Lookup up the method to call.
            function_pointer = cmd_table.get(command_string)
            
            # If the command_string is not recognised then process_data(..)
            # is called.
            if function_pointer:
                function_pointer()
            else:
                self.process_data(command_string)
            
def main():
    '''Initialises the logging, establishes a connection to scratch and
    then handles the scratch and printer IO.
    '''
    if platform.system() != 'Linux':
        sys.exit('This script has only been written for Linux')

    setup_logging()
    args = parse_arguments()

    # Connect to scratch
    scratch_conn = scratch.Scratch()

    try:
        # Introduce self to scratch
        scratch_conn.broadcast("Hello, Scratch!")

        # Pre-load name font
        font = pick_font(args.font)
        
        # Initialise USB  connectio with Pipsta
        (ep_out, ep_in) = setup_usb()
        query_serial_number(ep_out, ep_in)
        
        # Start processing messages from scratch
        listener = MessageListener(font, ep_out)
        listener.run(scratch_conn)
    except KeyboardInterrupt:
        # Expected exception, user has quit
        pass
    finally:
        # Say goodbye to scratch politely
        scratch_conn.broadcast("Goodbye scratch")
        scratch_conn.disconnect()

if __name__ == '__main__':
    main()
