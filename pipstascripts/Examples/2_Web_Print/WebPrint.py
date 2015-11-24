# WebPrint.py
# Copyright (c) 2014 Able Systems Limited. All rights reserved.
"""This simple code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

OVERVIEW
This python script builds on BasicPrint.py, adding functionality to issue
queries on a web-hosted MySQL database to retrieve as-yet unprinted
'print jobs'. Once the data is retrieved, each 'row' is sent to the printer in
turn, with a subsequent operation on the database marking each row as printed as
it is written to the OUT endpoint.

Copyright (c) 2014, Able Systems Ltd. All rights reserved.
"""

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
FEED_PAST_CUTTER = b'\n' * 5

# USB specific constant definitions
PIPSTA_USB_VENDOR_ID = 0x0483
PIPSTA_USB_PRODUCT_ID = 0xA053

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

PRINTER_SERIAL_NUMBER_MAX_LENGTH = 10
PRINT_JOB_POLL_PERIOD = 3

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
    '''Looks for an Pipsta on the USB.  If found the printer is configured and
    and the in/out bulk transfer endpoints are returned.
    '''

    # Find the Pipsta's specific Vendor ID and Product ID
    dev = usb.core.find(idVendor=PIPSTA_USB_VENDOR_ID,
                        idProduct=PIPSTA_USB_PRODUCT_ID)
    if dev is None:
        raise IOError('Printer not found')

    try:
        dev.reset()
        dev.set_configuration()
    except usb.core.USBError as ex:
        raise IOError('Failed to configure the printer', ex)

    # The following steps get an 'Endpoint instance' for both reading and
    # writing to the printer. It uses PyUSB's versatile find_descriptor
    # functionality to claim the interface and get a handle to the endpoint

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
        raise IOError('Could not find an endpoint to write to')
    if ep_in is None:  # check we have a real endpoint handle
        raise IOError('Could not find an endpoint to read from')

    purge_usb_input(ep_in)
    return (ep_in, ep_out)


def get_printer_id(ep_in, ep_out):
    '''Using the supplied USB endpoints a request for the printers ID is sent
    to the printer and then a response is read back.  Any white space is
    stripped.
    '''
    ep_out.write(QUERY_SERIAL_NUMBER)
    return ''.join([chr(x) for
                    x in ep_in.read(PRINTER_SERIAL_NUMBER_MAX_LENGTH)]).strip()

def process_print_jobs(printer_id, ep_out):
    '''Connects to the print job database using a set of credentials (URL, port,
    user name, password and database name) provided.  The printers serial number
    is used as an id to look up any print jobs outstanding.
    '''
    conn = None
    unprinted_jobs_cursor = None
    mark_job_printed_cursor = None
    try:
        # pylint: disable=W0142
        conn = MySQLdb.connect(**DB_CONFIG)
        unprinted_jobs_cursor = conn.cursor()
        mark_job_printed_cursor = conn.cursor()

        # Send a MySQL query to retrieve any unprinted data.  Note that the
        # parameter handling has been left to the MySQL API.  Leaving this to
        # the database minimises the risk of purposful (or accidental) SQL
        # injection attacks caused by malformed queries.
        try:
            unprinted_jobs_cursor.execute(
                "SELECT print_data, job_id " \
                "FROM printdata " \
                "WHERE printer_id = %s", printer_id)
        except MySQLdb.Error as e:
            print('Failed to retrieve any unprinted jobs: ' + str(e))
            raise

        # Loop to collect and print all of the unprinted
        for row in unprinted_jobs_cursor:
            ep_out.write(row[0].decode('hex'))
            ep_out.write(FEED_PAST_CUTTER)

            # Execute a MySQL 'query' to mark this row as printed thereafter
            try:
                mark_job_printed_cursor.execute(
                    "DELETE FROM printdata WHERE job_id = %s", (row[1],))
            except MySQLdb.Error as e:
                print('Failed to mark job as completed: ' + str(e))
                raise
        
        conn.commit()

    except MySQLdb.Error as err:
        print(err)
    finally:
        if unprinted_jobs_cursor:
            unprinted_jobs_cursor.close()
        if mark_job_printed_cursor:
            mark_job_printed_cursor.close()
        if conn:
            conn.close()  # Clean-up: Close the database


def signal_handler(signum, frame):
    """Simple signal handler that allows the process to be killed without
    super user privelages.

    For further information about Linux signals enter 'man -s7 signal' in the
    terminal on the raspberry pi (http://linuxmanpages.com/man7/signal.7.php).
    """
    del signum, frame # intentionally unused delete them to make it obvious
    sys.exit()

def main():
    '''Looks up any print jobs in the print database that have this printers id
    assigned to them, prints them out and marks the job as complete.
    '''
    if platform.system() != 'Linux':
        sys.exit('This script has only been written for Linux')
        
    parse_arguments()

    signal.signal(signal.SIGINT, signal_handler)
    (printer_in, printer_out) = connect_to_printer()
    printer_id = get_printer_id(printer_in, printer_out)

    assert printer_id != None
    assert printer_id != ''

    # check for any outstanding print jobs
    process_print_jobs(printer_id, printer_out)
    # got to sleep for a while, when awoken check for more work and sleep again
    while True:
        time.sleep(PRINT_JOB_POLL_PERIOD)
        process_print_jobs(printer_id, printer_out)

if __name__ == '__main__':
    main()
