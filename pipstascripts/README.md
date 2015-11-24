[![Pipsta Logo](https://bitbucket.org/repo/enq8r6/images/3048173118-Logo_small.jpg)](http://www.pipsta.co.uk)

# Websites #
Pipsta Website: http://www.pipsta.co.uk

Android NFC App: https://play.google.com/store/apps/details?id=com.pipsta.pipstanfcprinter

Buy Pipsta: http://www.modmypi.com/raspberry-pi/set-up-kits/project-kits/pipsta-the-little-printer-with-big-ideas/?search=pipsta


# What's New #
* The [Wiki](https://bitbucket.org/ablesystems/pipsta/wiki/Home) is on-line and new content is being added. Please bear with us as we migrate the docs to the Wiki!
* A QT4-based Graphical User interface demonstrating some of the demonstration scripts
* New printer firmware - fixes corruption of printout when printing over NFC
* New faster banner prints
* PNG image file printing
* A fun merit printing application combining images, fonts and QR codes
* A verification/diagnostic tool which confirms all the necessary modules are present and that the printer is connected correctly.

# What's Next #

We are currently working on a **CUPS driver for Pipsta**. This will ultimately allow printing from applications such as Leafpad, Geany and GIMP. We intend to release previews of the driver as we complete each development stage, i.e.

* text-only, 
* graphics rendering 
* full-featured driver.

If you would like to be involved in the beta testing of this driver, please [email us](mailto:support@pipsta.co.uk).

# README #

The python scripts and the documentation in this repository have been provided
to demonstrate how the Pipsta can be used in an educational or hobbyist
environment.  The Pipsta is a based around a
[Raspberry Pi](http://www.raspberrypi.org/) and a thermal printer.

### What is this repository for? ###

* Demonstration of the Pipsta
* Documentation of the setup of the Pipsta
* Documentation of the examples
* Proposed projects
* Beta
* [Learn Markdown](https://bitbucket.org/tutorials/markdowndemo)

### How do I get set up? ###

* Summary of set up
    * [Assemble the Pipsta](https://bytebucket.org/ablesystems/pipsta/src/master/Documents/PIPSTA002%20-%20Model%20B+%20Assembly%20Instructions.pdf)
    * [Install Raspbian and Pipsta Software on the Raspberry Pi](https://bitbucket.org/ablesystems/pipsta/src/master/Documents/PIPSTA004%20-%20Pipsta%20First-Time%20Setup.pdf).
    * Download the [latest sources from the repository](https://bitbucket.org/ablesystems/pipsta/downloads)
      to the [Raspberry Pi](http://www.raspberrypi.org/)
    * Copy this file to `/home/pi`

    ![Alt Text](https://bitbucket.org/ablesystems/pipsta/downloads/2014-11-28-100957_640x480_scrot.png "File Manager Screenshot" =160x120)

    * Right click on the downloaded file and select `xarchiver`.  When the
    window appears select the 'Action->Extract' and then click 'Extract'.
    * Rename the folder that has just been extracted to `pipsta`.
    * Double click on the 'pipsta' folder.
    * Double click on the 'Examples' folder.
    * Double click on the 'system_scripts' folder.
    *	Press **[F4]** to bring up another instance of the LXTerminal.
    * In order to disable the standard Linux printer, thereby permitting
    communication to the Pipsta printer, and allow the default user to have
    permissions to access the printer without having to be a ‘super-user’,
    enter the following lines at the $ prompt to copy files from this folder to
    the appropriate system folders.

        > sudo cp 60-ablesystems-pyusb.rules /etc/udev/rules.d

        > sudo cp usblp_blacklist.conf /etc/modprobe.d
 
        **In each case, ensure you have typed the space before the ‘/etc’.**

    * Finally, enter the following at the $ prompt. This will allow the above
    settings to be used:

        > sudo shutdown –r now

    * The system will now restart and boot to the graphical desktop.
    * Your Raspberry Pi is now set up with everything it needs to communicate
    with the Pipsta printer over the USB connection.

* Setting up the Pipsta Printer
    1. Apply power to the printer
    1. Press the ridged area at the back of the printer to open the paper
    compartment
    1. Load paper roll into printer, observing the orientation of the paper roll
    as shown the embossed legend in the base of the paper compartment.
    1. Remove a couple of turns of paper so the glue does not affect the print
    quality or printer mechanism
    1. Close the lid
    1. Check the printer’s LED is lit green and not flashing. If the LED is
    flashing, open the printer again and ensure the paper is aligned correctly
    in the printer mechanism
    1. Check the printer is functioning by double-clicking the button on the
    printer. A self-test message should be printed.

* Testing the System
    1. In the File Manager, go to the `pipsta\Examples\1_Basic_Print` folder
    1. Open a terminal window by pressing [F4]
    1. Run a simple Python script by entering the following at the $ prompt
    (note that Linux is case-sensitive):

         > python BasicPrint.py Hello from Pipsta\\!

    1. The Pipsta should now print this message to the paper roll in simple
    text. If not, check the troubleshooting steps below in Diagnosing Basic
    Printing Problems.
    1. Congratulations: you are now printing with Pipsta!

* Next Steps
    If this is the end of your session, see the section entitled Shutting
    Pipsta Down Safely, or –to continue on to more advanced applications—
    take the next step with any of the tutorials:

    [Tutorials Index](https://bitbucket.org/ablesystems/pipsta/wiki/Tutorials)

### Diagnosing Basic Printing Problems ###
**NEW** A script (`verify_pipsta_install.py`) has been added to the root of the project to try and help diagnose any installation issues.  The script checks OS, python and python libraries then it attempts to communicate with the printer.  If you would like any changes to the script then please feel free to send a request (or a patch) to <support@pipsta.co.uk>.

~~~
python verify_pipsta_install.py
~~~

| Problem | Possible Solution |
|------------|-----------------------|
| Printer LED not illuminated | Check both the power to the printer (on the back of the Pipsta) and the USB connection from Raspberry Pi to printer |
| Printer LED flashing green | Ensure the paper is loaded correctly |
| Printer LED flashing green-off-red-off | Ensure the printer power supply is present. Whilst the Raspberry Pi and Printer can communicate with just a USB connection, printing cannot take place without the printer power being applied |
| Permission error when running python script | Ensure you copied the system files to the correct locations by opening LXTerminal and pressing [UP ARROW] on the keyboard to review the previous terminal commands. |
| IO Error: Printer not found | Enter `ls /dev/a*` at the command line to list connected devices beginning with ‘a’. If you do not see ‘Ap1400’ listed, Linux cannot see the printer. Manually check that printer USB connectors are located correctly at both ends. |
| Issue not resolved by above checks | Remove the USB connection to the printer, wait a few seconds, then replace |
| Issue not resolved by above checks | Shut-down the Pi and remove power from both the Raspberry Pi and the printer. Reconnect power to both and wait for the unit to reboot |
| Issue not resolved by above checks | Send an email to <support@pipsta.co.uk> |

### Shutting Pipsta Down Safely ###
Whilst the printer is resilient when it comes to powering down, the Raspberry Pi must undergo a strict shutdown process to avoid corrupting the Micro SD card. 

* The most straightforward method of doing this is to double-click the ‘Shutdown’ icon on the desktop.
* If you are already in LXTerminal, type `sudo shutdown –h now` to shut-down the Raspberry Pi immediately.

**Always make sure ALL activity on the Raspberry Pi’s green LED (the LED on the right) has stopped before removing the power!**

### Upgrading the pipsta Firmware ###
A new tool (the fpu) has been created to allow pipsta firmware to be installed from Linux.  This has been packaged up for Raspbian and placed in the download page of this bitbucket site (along with the new firmware).  To install the new firmware follow the instrucitons below.

1. Download pipsta-printer-utilities-1.1.0-Linux.deb and V9_2_04.able to your Raspberry Pi.
1. Ensure you have libusb-dev installed `sudo apt-get install libusb-dev`
1. Install the printer utilities by running `sudo dpkg -i pipsta-printer-utilities-1.1.0-Linux.deb` from the directory the file is saved in.
1. Check the install `fpu --version`
1. Check the printer is connected to the Raspberry Pi `ls /dev/ap1400`
1. Install the new firmware `fpu V9.2.04.able`

If you have any problems please contact us.

### Who do I talk to? ###
* <support@pipsta.co.uk>

### Why Not Visit ###
* [Facebook](https://www.facebook.com/pages/Pipsta/921416174536872)
* [Twitter](https://twitter.com/PipstaPrinter)
* [Youtube](https://www.youtube.com/channel/UCPkYuupnqoPXgz6yDQcf0nQ)