# WebSend.py
# Copyright (c) 2014 Able Systems Limited. All rights reserved.
'''This simple code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

This script takes the supplied filename and copies the contents of that to
a new print job on the configured print job database.  The job is restricted
to the printer ID supplied.

Copyright (c) 2014 Able Systems Limited. All rights reserved.
'''
import argparse
import binascii
import sys

import MySQLdb

PRINTER_SERIAL_NUMBER_MAX_LENGTH = 10

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

def parse_args():
    '''Parses the arguments on the CLI and returns the list of arguments.  If
    any arguments are missing or invalid then a suitable error message is
    supplied
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('printer_id',
                        help='id of printer the job should be sent to')
    parser.add_argument('file', type=argparse.FileType('rb'),
                        help='a file to send to the printer')
    return parser.parse_args()

# Create a connection to the database and get a cursor to
def connect_to_db():
    '''Opens a connection to the database and returns a cursor that can be
    used to execute queries
    '''
    # pylint: disable=W0142
    dbc = MySQLdb.connect(**DB_CONFIG)
    return (dbc, dbc.cursor())

def insert_data(db_conn, cursor, printdata, printer_id):
    '''Creates a new print job in the database'''
    try:
        cursor.execute("INSERT INTO printdata(print_data, printer_id) " \
              "VALUES (%s, %s)", (printdata, printer_id))
        db_conn.commit()
    except MySQLdb.Error as ex:
        print('Error inserting data: ' + str(ex))
        raise


def read_uid(cursor):
    '''Obtains the next unique job id from the database'''
    try:
        cursor.execute("SELECT MAX(job_id) AS job FROM printdata")
        job = cursor.fetchone()
        if job is not None and job[0] is not None:
            return job[0] + 1
    except MySQLdb.Error as e:
        print('Error reading UID: ' + e)
        raise

    return 0

def main():
    '''Sends the contents of the supplied file to the print job database with
    the supplied printer serial number.
    '''

    # This application is written using the python2 API call 'raw_input', this
    # must be changed to the python3 API call 'input'.  The application has not
    # been tested under python3.
    if sys.version_info[0] > 2:
        sys.exit('This application was written for python2.')

    db_conn = None
    args = parse_args()

    try:
        (db_conn, cursor) = connect_to_db()
        read_uid(cursor)
        job = ""

        with args.file:
            # Get data from file
            for data in args.file:
                data = binascii.hexlify(data)
                job += data

            insert_data(db_conn, cursor, job, args.printer_id)

        print("Print job created!")

    except MySQLdb.Error as ex:
        print('Print job cancelled due to a previous error')
    finally:
        if db_conn:
            db_conn.close()

if __name__ == '__main__':
    main()
