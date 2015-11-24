# WebSendMany.py
# $Rev$
# Copyright (c) 2014 Able Systems Limited. All rights reserved.
"""This simple code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

A print job is created based on the supplied data file (to print) the printer
serial number (',' seperated list of target printers) and a list of credentials
the printer must have for the job to be executed

Copyright (c) 2014 Able Systems Limited. All rights reserved.
"""
import argparse
import binascii

import MySQLdb

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
    """Parses the arguments the user supplies, returning the verified list
    of arguments.  Any errors are pointed out to the user.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('printer_id', nargs='+',
                        help='id of printer the job should be sent to')
    parser.add_argument('file', type=argparse.FileType('r'),
                        help='a file to send to the printer')
    parser.add_argument('-c', '--credentials', help='credentials string')
    return parser.parse_args()

def insert_data(db_conn, printdata, printer_ids, credentials=None):
    """Uses the database connection supplied, inserts a print job into the
    database.
    """
    try:
        cursor = db_conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(group_id),0) FROM printer_jobs")
        group_id = cursor.fetchone()[0] + 1

        for printer_id in printer_ids:
            if credentials == None:
                cursor.execute(
                    "INSERT INTO printer_jobs VALUES(%s, %s, FALSE, NULL);",
                    (group_id, printer_id))
            else:
                cursor.execute(
                    "INSERT INTO printer_jobs VALUES(%s, %s, FALSE, %s);",
                    (group_id, printer_id, credentials))

        cursor.execute(
            "INSERT INTO printdata_v2 VALUES (null, %s, %s);",
            (printdata, group_id))
        db_conn.commit()
    except MySQLdb.Error as err:
        print(err)

def main():
    """Main loop for the application.  Connects to the database and stores a
    new print job.
    """
    args = parse_arguments()
    db_conn = None

    try:
        # pylint: disable=W0142
        db_conn = MySQLdb.connect(**DB_CONFIG)

        with args.file:
            job = ""
            # Get data from file
            for data in args.file:
                job += binascii.hexlify(data)

            if args.credentials:
                insert_data(db_conn, job, args.printer_id, args.credentials)
            else:
                insert_data(db_conn, job, args.printer_id)

        print("Print job created!")
    finally:
        if db_conn:
            db_conn.close()

if __name__ == '__main__':
    main()
