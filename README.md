#This is our Capstone Project for the Tarlac State University. I created this repo to minimize the work on installing the major packages required on my Raspberry Pi Kiosk project for Tarlac City

#INSTALLATION NOTES

#Installing Pipsta Debian packages
sudo dpkg -i pipstautil.deb

#Installing wiringPi (controlling GPIO via Web)
cd wiringPi/  
./build

#Verify wiringPi installation
gpio readall

#Installing pyusb
python setupy.py install

#Installing Pipsta permissions
cd pipstascripts/Examples/system_scripts  
sudo cp usblp_blacklist.conf /etc/modprobe.d  
sudo cp 60-ablesystems-pyusb.rules /etc/udev/rules.d  
sudo reboot

#Required packages for Pipsta
sudo apt-get install python-pip python-dev  
sudo apt-get install libffi-dev  
sudo apt-get install python-mysqldb 
sudo apt-get install python-qt4  
sudo apt-get install libusb-dev  
sudo pip install feedparser  
sudo pip install flask  
sudo pip install argparse  
sudo pip install bitarray  
sudo pip install pillow  
sudo pip install qrcode  
sudo pip install fclist

#Verify Pipsta installation
cd pipstascripts/  
python verify_pipsta_install.py

#UnClutter to Disable Mouse Pointer for Kiosk Mode
sudo apt-get install x11-xserver-utils unclutter

#Raspberry Pi 2 Model B autostarts
sudo nano ~/.config/lxsession/LXDE-pi/autostart

#Enable unclutter (paste this in RPi2 autostarts)
@unclutter -idle 0.0

#Screensaver and Blanking disabler
sudo apt-get install xscreensaver

#Credits to wiringPi developer, Python developers and Pipsta Thermal Printer Developers. Hoping that, me and my team will pass the capstone project. God bless us.
