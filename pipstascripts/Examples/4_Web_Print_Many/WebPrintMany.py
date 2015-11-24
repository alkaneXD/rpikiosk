# WebPrintMany.py
# $Rev$
# Copyright (c) 2014 Able Systems Limited. All rights reserved.
'''This simple code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

This script connects to the print job database and identifies all of the jobs
destined for this printer.  If the job specifies any credentials then the
printer is queried to verify if it has matching credentials

Copyright (c) 2014, Able Systems Ltd. All rights reserved.
'''

import argparse
import platform
import signal
import sys
import time

from usb.core import USBError
import usb.core
import usb.util

import MySQLdb


# Query for printer serial number
QUERY_SERIAL_NUMBER = b'\x1dI\x06' # GS,'I',6
QUERY_CREDENTIALS = b'\x1dI\x7e' # GS,'I',126
FEED_PAST_CUTTER = b'\n' * 5

# USB specific constant definitions
PIPSTA_USB_VENDOR_ID = 0x0483
PIPSTA_USB_PRODUCT_ID = 0xA053

PRINTER_SERIAL_NUMBER_MAX_LENGTH = 10
PRINTER_CREDENTIALS_MAX_LENGTH = 65536
PRINT_JOB_POLL_PERIOD = 3

# DB_NAME specific constants
# Insert your database connection credentials here.
# Refer to Pipsta documents PIPSTA010..PIPSTA012
DB_CONFIG = {
  'user': 'user_name_db',
  'passwd': 'password',
  'host': 'host_ip_address',
  'db': 'user_name_db',
  'port': ????,
}

def parse_arguments():
    '''This scripts expects no arguments, offers help text and that is all.'''
    parser = argparse.ArgumentParser(description='Polls the print server')
    return parser.parse_args()
    
def purge_usb_input(usb_in):
    '''Removes any data from the usb input that may be left over from a
    previous connection.
    '''
    while True:
        try:
            dummy = usb_in.read(1)
        except USBError as dummy:
            break

def connect_to_printer():
    '''Establishes a read/write connection to the 1st Pipsta found on the USB
    bus.
    '''

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
    except usb.core.USBError as ex:
        raise IOError('Failed to configure the printer', ex)

    cfg = dev.get_active_configuration()  # Get a handle to the active interface

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

    ep_in = usb.util.find_descriptor(
        intf,
        custom_match=lambda e:
        usb.util.endpoint_direction(e.bEndpointAddress) ==
        usb.util.ENDPOINT_IN
    )

    if ep_out is None:  # check we have a real endpoint handle
        raise IOError('Could not find an endpoint to print to')

    if ep_in is None:  # check we have a real endpoint handle
        raise IOError('Could not find an endpoint to read from')

    purge_usb_input(ep_in)
    return (ep_in, ep_out)

def get_printer_id(ep_in, ep_out):
    '''Requests the printer ID from the printer and then returns the
    serial number with any white space stripped from the start/end of the
    string.
    '''
    ep_out.write(QUERY_SERIAL_NUMBER)
    return ''.join([chr(x) for
                    x in ep_in.read(PRINTER_SERIAL_NUMBER_MAX_LENGTH)]).strip()

def get_credentials(ep_in, ep_out):
    '''Requests the NFC credentials from the printer and then returns the
    credentials.  If no credentials are loaded on the printer then a None
    is returned.
    '''
    result = None

    try:
        ep_out.write(QUERY_CREDENTIALS)
        result = ep_in.read(PRINTER_CREDENTIALS_MAX_LENGTH)
    except usb.core.USBError as err:
        if 'timed out' in err.args[1]:
            pass
        else:
            exc_info = sys.exc_info()
            raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])

    if not result:
        return None

    return ''.join([chr(x) for x in result]).split(',')


def process_print_jobs(ep_in, ep_out):
    '''Looks up any print jobs for the Pipsta connected and filters the
    jobs by the supplied credentials (if any exist) and finally prints any
    outstanding jobs.
    '''
    try:
        printer_id = get_printer_id(ep_in, ep_out)
        credentials = get_credentials(ep_in, ep_out)
    except USBError as err:
        # Failed to connect to a printer, abort
        return
    
    # The with statement is used to manage connections to the database and to
    # manage database cursors.  SQLErrors are caught to help diagnose database
    # issues.  USBError's are not expected so are not handled explicitly, the
    # use 'while-statements' ensures that no matter what the database
    # connections will be tidied up.  The pyusb library claims to always leave
    # the usb in a correct state on exit.
    #
    # Everytime a call is made to MySQLdb.connect in a with statement a cursor
    # is returned for use on the database.  To get multiple cursors multiple
    # calls to MySQLdb.connect are made.
    
    # pylint: disable=W0142
    with MySQLdb.connect(**DB_CONFIG) as unprinted_jobs_cursor:
        try:
            # If the printer has credentials then use these (along with the
            # printer ID) to filter the print jobs.  If there are no credentials
            # then look for print jobs that don't require any credentials and
            # that are intended for this printer. 
            if credentials:
                format_strings = ','.join(['%s'] * len(credentials))
                unprinted_jobs_cursor.execute('''
SELECT print_data, job_id
FROM printdata_v2 AS d
INNER JOIN printer_jobs AS j ON  d.print_group_id = j.group_id
WHERE printer_id = %s AND printed = FALSE AND credentials IN (%s)''' %
('%s', format_strings), (printer_id,) + tuple(credentials))
            else:
                unprinted_jobs_cursor.execute('''
SELECT print_data, job_id
FROM printdata_v2 AS d
INNER JOIN printer_jobs AS j ON d.print_group_id = j.group_id
WHERE printer_id = %s AND printed = FALSE AND credentials IS NULL''',
printer_id)    
            # Obtain the 1st print job intended for this printer and with a set
            # of credentials that match.
            row = unprinted_jobs_cursor.fetchone()
            
            # Print the job, mark it as complete and collect the next print job
            while row:
                with MySQLdb.connect(**DB_CONFIG) as mark_job_printed_cursor:
                    ep_out.write(row[0].decode('hex'))
                    ep_out.write(FEED_PAST_CUTTER)
                    mark_job_printed_cursor.execute('''
UPDATE printdata_v2 AS d
INNER JOIN printer_jobs AS j ON d.print_group_id = j.group_id
SET printed = TRUE
WHERE job_id = %s AND printer_id = %s AND printed = FALSE''',
(row[1], printer_id))
                    # Retrieve the next row
                    row = unprinted_jobs_cursor.fetchone()

        # Format and print any database errors (along with executed statement)
        except MySQLdb.Error as err:
            # pylint: disable=W0212
            print(unprinted_jobs_cursor._last_executed)
            print(err)

def signal_handler(sig_int, frame):
    '''This signal handler negates the need for super user rights when ending
    this application usgin the 'kill' command.
    '''
    del sig_int, frame
    sys.exit()

def main():
    '''Connect to the printer and the database at regular intervals.  If there
    are any valid print jobs outstanding then print them off.
    '''
    if platform.system() != 'Linux':
        sys.exit('This script has only been written for Linux')
    
    parse_arguments()
        
    signal.signal(signal.SIGINT, signal_handler)
    ep_in, ep_out = connect_to_printer()
    process_print_jobs(ep_in, ep_out)
    
    # go to sleep for a while, when awoken check for more work and sleep again
    while True:
        time.sleep(PRINT_JOB_POLL_PERIOD)
        process_print_jobs(ep_in, ep_out)

if __name__ == '__main__':
    main()
