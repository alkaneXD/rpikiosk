#This is our Capstone Project for the Tarlac State University. I created this repo to minimize the work on installing the major packages required on my Raspberry Pi Kiosk project for Tarlac City

#INSTALLATION NOTES

#Add Debian Wheezy sources.list to get Debian Wheezy packages
sudo nano /etc/apt/sources.list  
deb http://archive.raspbian.org/raspbian wheezy main contrib non-free rpi  
deb-src http://archive.raspbian.org/raspbian wheezy main contrib non-free rpi  
sudo apt-get update  
sudo apt-get upgrade

#Installing Pipsta Debian packages
sudo apt-get install libusb-1.0.0-dev  
sudo apt-get install libusb-dev  
sudo dpkg -i pipstautil.deb

#Installing wiringPi (controlling GPIO via Web)
cd wiringPi/  
sudo sh ./build

#Verify wiringPi installation
gpio readall

#Installing Pipsta permissions
cd pipstascripts/Examples/system_scripts  
sudo cp usblp_blacklist.conf /etc/modprobe.d  
sudo cp 60-ablesystems-pyusb.rules /etc/udev/rules.d

#Required packages for Pipsta
sudo apt-get install python-dev  
sudo apt-get install python-pip  
sudo apt-get install libffi-dev  
sudo apt-get install python-mysqldb  
sudo apt-get install python-qt4  
sudo pip install pyusb --pre  
sudo pip install feedparser  
sudo pip install flask  
sudo pip install argparse  
sudo pip install bitarray  
sudo pip install pillow / sudo easy_install pillow  
sudo pip install qrcode  
sudo pip install fclist  
sudo reboot

#Installing Web Server for Raspberry Pi 2
sudo apt-get install apache2 php5 libapache2-mod-php5  
sudo service apache2 restart  
sudo apt-get install mysql-server mysql-client php5-mysql

#Install FTP for easy Web server upload
sudo chown -R pi /var/www/html  
sudo apt-get install vsftpd  
sudo nano /etc/vsftpd.conf  
write_enable=YES  
force_dot_files=YES  
ln -s /var/www/html ~/uploadhere

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

#Credits to wiringPi developer, Python developers and Pipsta Thermal Printer Developers. God bless us.
