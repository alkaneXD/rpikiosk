# improvedlisten.py
# Copyright (c) 2014 Able Systems Ltd. All rights reserved.
"""
This example is based on the documentation at
https://github.com/pilliq/scratchpy and is intended to work with the scratch
project 'improved_scratch.sb'

Copyright (c) 2014 Able Systems Ltd. All rights reserved.
"""

import scratch
import usb.core
import usb.util
import platform

def connect_to_printer():
    '''Looks for the 1st Pipsta printer connected to the systems USB
    bus. An IOError exception is thrown when -

    * A printer cannot be found
    * The printers USB connection cannot be configured
    * An endpoint to send to commands to cannot be found
    * An endpoint to receive printer responses cannot be found
    * A control endpoint for the printer cannot be found'''
    vid = 0x0483
    pid = 0xA053

    # Find the Pipsta's specific Vendor ID and Product ID (also known as vid
    # and pid)
    dev = usb.core.find(idVendor=vid, idProduct=pid)
    if dev is None:  # if no such device is connected...
        raise IOError('Printer not found')  # ...report error

    try:
        if platform.system() == 'Linux':
            dev.reset()

        # Initialisation. Passing no arguments sets the configuration to the
        # currently active configuration.
        dev.set_configuration()
    except usb.core.USBError as ex:
        raise IOError('Failed to configure the printer', ex)

    # The following steps get an 'Endpoint instance'. It uses
    # PyUSB's versatile find_descriptor functionality to claim
    # the interface and get a handle to the endpoint
    # An introduction to this (forming the basis of the code below)
    # can be found at:
    #

    cfg = dev.get_active_configuration()  # Get a handle to the active interface

    interface_number = cfg[(0, 0)].bInterfaceNumber
    # added to silence Linux complaint about unclaimed interface, it should be
    # released automatically
    usb.util.claim_interface(dev, interface_number)
    alternate_setting = usb.control.get_interface(dev, interface_number)
    interface = usb.util.find_descriptor(
        cfg, bInterfaceNumber=interface_number,
        bAlternateSetting=alternate_setting)

    pr_out = usb.util.find_descriptor(
        interface,
        custom_match=lambda e:
        usb.util.endpoint_direction(e.bEndpointAddress) ==
        usb.util.ENDPOINT_OUT
    )

    if pr_out is None:
        raise IOError("Could not find an endpoint to send printer commands to")

    return(dev, pr_out)

def listen(scratch_connection):
    '''Sets up an infinite loop, yielding control when a message is received
    or the user has halted the application using a Ctrl-C'''
    while True:
        try:
            yield scratch_connection.receive()
        except scratch.ScratchError:
            raise StopIteration

def get_printer_id(printer):
    '''Obtains a printers id using the USB control interface, this allows the
    printer ID to be extracted when the printer is only connected via USB'''
    res = printer.ctrl_transfer(0xC0, 0x0d, 0x0106, 0, 10)
    return ''.join([chr(x) for x in res])

def print_footer(printer_out):
    '''Prints a standard footer, 5 new lines ensures the text is clear of the
    cutter'''
    printer_out.write('\n'*5)
    
def set_double_height(printer_out):
    '''Sets the text to double height, clears the underline and double width
    flags'''
    printer_out.write('\x1b!\x10')
    
def set_double_width(printer_out):
    '''Sets the text to double width, clears the underline and double height
    flags'''
    printer_out.write('\x1b!\x20')

def set_underlined(printer_out):
    '''Sets the text to underlined, clears the double height and double width
    flags'''
    printer_out.write('\x1b!\x80')

def set_normal(printer_out):
    '''Clears the underlined, double height and double width flags'''
    printer_out.write('\x1b!\x00')

def send_barcode(printer_out, txt):
    '''Sends the supplied text as a CODE39 barcode'''
    # Set automatic text in barcode to print beneath bars
    cmd = '\x1dH\x02'
    printer_out.write(cmd)
    
    # Set width of barcode to minimum for maximum barcode length
    # NB: long barcodes may be truncated without warning!
    cmd = '\x1dw\x02'
    printer_out.write(cmd)

    # Print the data as a Code39 barcode
    cmd = '\x1dk\x04{}\x00'.format(txt)
    printer_out.write(cmd)

def print_to_pipsta(printer_out, txt, is_barcode):
    '''Sends the text as text or barcode, then adds a footer to the print out'''
    if is_barcode == True:
        send_barcode(printer_out, txt)
    else:
        printer_out.write(txt)
    
    print_footer(printer_out)

def main():
    '''Instantiates a connection to scratch. Broadcast our existance to scratch
    and then listen for any commands from the scratch environment.'''
    printing_barcode = False
    scratch_conn = scratch.Scratch()
    scratch_conn.broadcast("Hello, Scratch!")

    try:
        (printer, pr_out) = connect_to_printer()
        scratch_conn.sensorupdate({"SerialNumber":get_printer_id(printer)})
        scratch_conn.broadcast("SerialNumber")
        
        for msg in listen(scratch_conn):
            if msg[0] == 'broadcast':
                # Handle able command types
                if msg[1] == 'cmd_barcode3of9':
                    printing_barcode = True
                elif msg[1] == 'cmd_doubleHeight':
                    set_double_height(pr_out)
                    printing_barcode = False
                elif msg[1] == 'cmd_doubleWidth':
                    set_double_width(pr_out)
                    printing_barcode = False
                elif msg[1] == 'cmd_underlined':
                    set_underlined(pr_out)
                    printing_barcode = False
                elif msg[1] == 'cmd_normalText':
                    set_normal(pr_out)
                    printing_barcode = False
                else:
                    print_to_pipsta(pr_out, msg[1], printing_barcode)
                    printing_barcode = False
    except KeyboardInterrupt:
        # Normal way of exiting app, anything else will raise an error
        pass
    except IOError as error:
        print('Failed to connect to printer {}'.format(error))
    finally:
        # If the failure is expected or not - close down gracefully
        scratch_conn.disconnect()

if __name__ == '__main__':
    main()
