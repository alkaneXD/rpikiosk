# config.py
# $Rev$
# Copyright (c) 2015 Able Systems Limited. All rights reserved.
'''This code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

Copyright (c) 2015, Able Systems Ltd. All rights reserved.
'''
from launcher import Example

EXAMPLES = [
    Example().set_name('Basic Print')
             .set_description('Prints the supplied text to the Pipsta')
             .set_script('Examples/1_Basic_Print/BasicPrint.py')
             .set_editor('Text'),
    Example().set_name('Banner Print')
             .set_description('Prints the supplied text as a banner to '
                              'the Pipsta')
             .set_script('Examples/6_Banner_Print/banner.py')
             .set_editor('StyledText'),
    Example().set_name('QR Print')
             .set_description('Encodes the supplied text as a QR Code '
                              'and prints it to the Pipsta')
             .set_script('Examples/7_QR_Print/qr.py')
             .set_editor('Text'),
    Example().set_name('Image Print')
             .set_description('Prints a greyscale image to the Pipsta')
             .set_script('Examples/8_Image_Print/image_print.py')
             .set_editor('Image'),
    Example().set_name('Merit Print')
             .set_description('Prints a certificate for a student to '
                              'the Pipsta')
             .set_script('Examples/9_Merit_Printer/merit_printer.py')
             .set_editor('MeritForm'),
]
