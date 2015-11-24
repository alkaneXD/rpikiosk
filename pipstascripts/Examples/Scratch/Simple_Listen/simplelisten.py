# simplelisten.py
# Copyright (c) 2014 Able Systems Ltd.All rights reserved.
"""
This example is based on the documentation at
https://github.com/pilliq/scratchpy and is intended to work with the scratch
project 'simple_scratch.sb'

Copyright (c) 2014, Able Systems Ltd. All rights reserved.
"""

import scratch

def listen(scratch_conn):
    '''Sets up an infinite loop, yielding control when a message is received
    or the user has halted the application using a Ctrl-C'''
    while True:
        try:
            yield scratch_conn.receive()
        except scratch.ScratchError:
            raise StopIteration

def main():
    '''Instantiates a connection to scratch. Broadcast our existance to scratch
    and then listen for any commands from the scratch environment.'''
    scratch_conn = scratch.Scratch()
    scratch_conn.broadcast("Hello, Scratch!")

    try:
        for msg in listen(scratch_conn):
            if msg[0] == 'broadcast':
                # Handle able command types
                if msg[1] == 'cmd_barcode3of9':
                    print('barcode setup')
                elif msg[1] == 'cmd_doubleHeight':
                    print('double height setup')
                else:
                    print(msg[1])
    except KeyboardInterrupt:
        # Normal way of exiting app, anything else will raise an error
        pass
    finally:
        # If the failure is expected or not - close down gracefully
        scratch_conn.disconnect()

if __name__ == '__main__':
    main()
