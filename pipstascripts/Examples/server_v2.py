#!/usr/bin/python
# server_v2.py
# $Rev$
# Copyright (c) 2014 Able Systems Limited. All rights reserved.
"""This simple code example is provided as-is, and is for demonstration
purposes only. Able Systems takes no responsibility for any system
implementations based on this code.

This script accepts an argument of stop,start or restart and performs that
operation on the 1st instance of '4_Web_Print_Many/WebPrintMany.py' that is found
in the process list.

Copyright (c) 2014 Able Systems Limited. All rights reserved.
"""
import argparse
import os
import signal
import subprocess

def parse_args():
    """Parse the arguments supplied.  Returns a list of valid arguments, prints
    an error message reporting any missing or invalid arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('operation',
                        choices=['start', 'stop', 'restart'],
                        help='start/stop/restart the server')
    return parser.parse_args()


def find_server_process(components):
    """Looks up the 1st process with a name that contains 'python' and
    'Webprint' and returns the processes handle.
    """
    proc = subprocess.Popen(['ps', '-o', 'pid,command'],
                            stdout=subprocess.PIPE)
    (out, dummy) = proc.communicate()
    
    # Take the result, split into records, remove 1st record (column headers)
    # and finally remove leading/trailing white space
    processes = [i.strip() for i in str(out).split('\n')[1:] if i]

    # Find the specified process and return
    if len(processes) > 0:
        for line in processes:
            fields = line.split(None, 1)
            if fields[1] == ' '.join(components):
                return int(fields[0])

    return None

def get_absolute_filename(relative_name):
    """Takes the supplied relative path and returns an absolute path"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__),
                                        relative_name))


def main():
    """The main loop of the application.  This application parses the CLI for
    arguments.  The following areguments are recognised -

    * start   - start a new instance of '4_Web_Print_Many/WebPrintMany.py'
    * stop    - stops the 1st instance of '4_Web_Print_Many/WebPrintMany.py'
    found running
    * restart - performs a stop then a start
    """
    args = parse_args()
    launch_command = ['python',
                      get_absolute_filename('4_Web_Print_Many/WebPrintMany.py')]
    pid = find_server_process(launch_command)

    if args.operation == 'start':
        if not pid:
            proc = subprocess.Popen(launch_command)
            print('Print job monitor service started - PID={}'.format(proc.pid))
        else:
            print('Print job monitor service  is already running')

    elif args.operation == 'stop':
        if pid:
            print('Stopping job monitor service - PID={}'.format(pid))
            os.kill(pid, signal.SIGTERM)
        else:
            print('No print job monitor was found to be running')
    elif args.operation == 'restart':
        if pid:
            print('Stopping job monitor service - PID={}'.format(pid))
            os.kill(pid, signal.SIGTERM)
        else:
            print('No print job monitor was found to be running')

        proc = subprocess.Popen(launch_command)
        print('Print job monitor service started - PID={}'.format(proc.pid))

if __name__ == '__main__':
    main()
