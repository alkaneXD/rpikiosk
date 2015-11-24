import os

def send_to_printer(params):
    if params == 'reboot':
        os.system('sudo reboot')
    else:
        os.system('sudo poweroff')
