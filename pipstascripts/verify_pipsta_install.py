# verify_pipsta_install.py
# Copyright (c) 2014 Able Systems Limited. All rights reserved.
import argparse
import platform
import sys
import socket
import fcntl
import struct
import array

FEED_PAST_CUTTER = b'\n' * 5

PIPSTA_USB_VENDOR_ID = 0x0483
PIPSTA_USB_PRODUCT_ID = 0xA053

# The following function was taken from http://stackoverflow.com/questions/24196932
def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
    
# The following was taken from http://code.activestate.com/recipes/439093/
def all_interfaces():
    max_possible = 128  # arbitrary. raise if needed.
    bytes = max_possible * 32
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', '\0' * bytes)
    outbytes = struct.unpack('iL', fcntl.ioctl(
        s.fileno(),
        0x8912,  # SIOCGIFCONF
        struct.pack('iL', bytes, names.buffer_info()[0])
    ))[0]
    namestr = names.tostring()
    return [namestr[i:i+32].split('\0', 1)[0] for i in range(0, outbytes, 32)]

def module_exists(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return False

    return True

def os_check():
    return (platform.system() == 'Linux')
    
def python_check():
    ok = (sys.version_info > (2, 6) and sys.version_info < (3, 0))

    if not ok:
        print('The demoes are targeted at python2 versions 2.6 and above')

    return ok
    
def pyusb_check():
    ok = module_exists('usb') == True and module_exists('usb.core') == True \
        and module_exists('usb.util') == True

    if not ok:
        print('The Pipsta is connected over USB, the demoes all depend on '
              'the pyusb module')

    return ok
    
def pillow_check():
    if not module_exists('PIL.Image'):
        print('The Pillow library for python is not installed and is required '
              'by most of the demoes')
        return False
    
    return True
    
def usb_enumeration_check():
    import usb.core
    dev = usb.core.find(idVendor=PIPSTA_USB_VENDOR_ID,
                        idProduct=PIPSTA_USB_PRODUCT_ID)
    assert dev, 'Printer failed to enumerate'
    return dev
    
def wait_for_printer(dev):
    import struct
    status = struct.unpack('B', dev.ctrl_transfer(0xC0, 0x0d, 0x0200, 0, 1))[0]
    while status & 0x40 == 0x40:
        print('Printer is in error state can you check the following -')
        print('  Paper is installed')
        print('  Printers power supply is connected')
        print('  The LED on the front of the panel is a constant green')
        raw_input('Press return to continue ')
        status = struct.unpack('B', dev.ctrl_transfer(0xC0, 0x0d, 0x0200, 0, 1))[0]
        
def get_default_interface(dev, cfg):
    import usb.core
    interface_number = cfg[(0, 0)].bInterfaceNumber
    usb.util.claim_interface(dev, interface_number)
    alternate_setting = usb.control.get_interface(dev, interface_number)
    interface = usb.util.find_descriptor(
        cfg, bInterfaceNumber=interface_number,
        bAlternateSetting=alternate_setting)
    return interface

def check_bulk_read(interface):  
    import usb.core  
    usb_in = usb.util.find_descriptor(
        interface,
        custom_match=lambda e:
        usb.util.endpoint_direction(e.bEndpointAddress) ==
        usb.util.ENDPOINT_IN
    )
    assert usb_in, 'No bulk in endpoint found for printer'
    from usb.core import USBError
    try:
        junk = usb_in.read(1)
        while junk:
            print(junk)
    except USBError as unused:
        pass
        
    return usb_in
    
def check_bulk_write(interface):
    import usb.core
    usb_out = usb.util.find_descriptor(
        interface,
        custom_match=lambda e:
        usb.util.endpoint_direction(e.bEndpointAddress) ==
        usb.util.ENDPOINT_OUT
    )
    assert usb_out, 'No bulk out endpoint found for printer'
    return usb_out

def ok_if_found(found):
    return 'Ok' if found else 'Missing'

def perform_connection_test(core, web, gui):
    dev = usb_enumeration_check()

    # Configure USB connection
    dev.reset()
    dev.set_configuration()
    cfg = dev.get_active_configuration()
    assert cfg, 'Failed to find an active configuration for the printer'

    # Check printer is powered
    wait_for_printer(dev)
    interface = get_default_interface(dev, cfg)

    usb_in = check_bulk_read(interface)
    usb_out = check_bulk_write(interface)

    # Check full bulk communications
    usb_out.write(b'\x1dI\x06')
    printer_id = usb_in.read(9)
    assert printer_id and printer_id != '', 'Printer did not respond with a valid ID'
    
    print('Successful bi-directional bulk communications established with '
          'printer')

    # Print, results
    printer_id = ''.join([chr(c) for c in printer_id]).strip()
    usb_out.write('Welcome to Pipsta ({})\n'.format(printer_id))
    (distname, linux_version, linux_id) = platform.linux_distribution()
    usb_out.write('Running on {} V{}\n'.format(distname, linux_version))
    (system, node, release, version, machine, processor) = platform.uname()
    usb_out.write('Based on {} V{} for\n'.format(system, release))
    usb_out.write('{} with {} arch.\n\n'.format(node, machine))
    
    for interface in all_interfaces():
        address = get_ip_address(interface)
        usb_out.write('{}\t{}\n'.format(interface, address))
        
    usb_out.write('\nRunning python V{}.{}\n\n'.format(
        sys.version_info[0], sys.version_info[1]))
    usb_out.write('OS            = Ok\n')
    usb_out.write('Python        = Ok\n')
    usb_out.write('    struct    = Ok\n')
    usb_out.write('    Pillow    = {0}\n'.format(ok_if_found(core[0])))
    usb_out.write('    bitarray  = {0}\n'.format(ok_if_found(core[1])))
    usb_out.write('    qrcode    = {0}\n'.format(ok_if_found(core[2])))
    usb_out.write('    MySQLdb   = {0}\n'.format(ok_if_found(web)))
    usb_out.write('    PyQt4     = {0}\n'.format(ok_if_found(gui[0])))
    usb_out.write('    fclist    = {0}\n'.format(ok_if_found(gui[1])))
    
    usb_out.write(FEED_PAST_CUTTER)

def main():
    print('Testing the Pipsta installation')

    os_ok = os_check()

    if os_ok == False:
        sys.exit("The demoes are written for Raspberry-Pi's running Raspbian")
        
    py_ok = python_check()
    pyusb_ok = False
    bitarray_ok = False
    pillow_ok = False
    qr_code_ok = False
    mysql_db_ok = False
    struct_ok = False
    pyqt4_ok = False
    fclist_ok = False

    if py_ok == False:
        print('Install python2 versions 2.6 or greater. Try one of -')
        print('    sudo apt-get install python2.6')
        print('or')
        print('    sudo apt-get install python2.7')
        print
    else:
        try:
            pyusb_ok = pyusb_check()
            bitarray_ok = module_exists('bitarray')
            pillow_ok = pillow_check()
            qrcode_ok = module_exists('qrcode')
            mysql_db_ok = module_exists('MySQLdb')
            struct_ok = module_exists('struct')
            pyqt4_ok = module_exists('PyQt4')
            fclist_ok = module_exists('fclist')
        except AssertionError as e:
            print(e)
            pass
        
    print('The following problems were found that may prevent you '
          'running all of the examples.')
    print
    print('To install python modules we uses pip.  To install pip try -')
    print('    sudo apt-get install python-pip python-dev')
    print

    if pyusb_ok == False or pillow_ok == False or bitarray_ok == False \
                    or qrcode_ok == False or struct_ok == False:
        print('The following will install the basic dependencies -')
        cmd_str = '    sudo pip install '
        if pyusb_ok == False:
            cmd_str += 'pyusb '
        if bitarray_ok == False:
            cmd_str += 'bitarray '
        if pillow_ok == False:
            cmd_str += 'Pillow '
        if qrcode_ok == False:
            cmd_str += 'qrcode '
        if struct_ok == False:
            cmd_str += 'struct '
        print(cmd_str)
        print

    if mysql_db_ok == False:
        print('The following will install the database dependencies -')
        print('    sudo pip install MySQLdb')
        print

    if pyqt4_ok == False or fclist_ok == False:
        print('The following will install the GUI dependencies -')
        print('    sudo apt-get install python-qt4 libffi-dev ')
        print('    sudo pip install fclist')
        print

    if pyusb_ok and struct_ok:
        print('Performing a simple connection test')
        perform_connection_test(core=(pillow_ok, bitarray_ok, qrcode_ok),
                                web=(mysql_db_ok), gui=(pyqt4_ok, fclist_ok))
        sys.exit()

# Ensure that BasicPrint is ran in a stand-alone fashion (as intended) and not
# imported as a module. Prevents accidental execution of code.
if __name__ == '__main__':
    main()

