# Software Installation Manual

## Introduction

- This manual will go through the necessary steps to install the software on the Raspberry Pi.
- You can also skip the installation process by downloading the system image file directly from [some link] and writing it to the SD card of Raspberry Pi. The system image file contains the configured operating system and the software source code file necessary for the Naloxone safety kit to run. 

## Necessary Equipment

- Raspberry Pi 3B+ or 4 with its power supply;
- SD Card >= 16GB;
- SD Card Reader;
- Physical Keyboard;
- Physical Mouse;
- Video cables;
- Monitor;
- Stable Internet Connection.

## Chapter 1: Download the Raspbian OS

This chapter will go through the necessary steps to download and write the Raspbian OS for the Raspberry Pi. You can skip this chapter if you already have a working operating system installed on the Raspberry Pi.

### Step 1.1: Download Raspberry Pi Imager

- Download the Raspberry Pi Imager from [Raspberry Pi OS](https://www.raspberrypi.com/software/). After downloading, follow the steps to install the software.

### Step 1.2: Open Raspberry Pi Imager

- Open the Raspberry Pi Imager, and you should see a window like

    ![Raspberry Pi Imager Window.](Screenshot%202022-12-26%20at%203.24.01%20AM.png)

### Step 1.3: Choose Operating System

- Click on the “CHOOSE OS” button. In the popup window, select “Raspberry Pi OS Full (32-bit)”. Currently, the software has only been tested on 32-bit operating systems.

    ![Choosing Operating System.](Screenshot%202022-12-26%20at%203.25.47%20AM.png)

- Alternatively, if you decide to use the image file provided, select “Use Custom” in the popup window and select the image file you just downloaded.

    ![Use the custom image provided.](Screenshot%202022-12-26%20at%203.38.30%20AM.png)

### Step 1.4: Choose Storage

- Insert the SD card into the SD card reader, then plug the SD Card reader into the USB port of your computer.
- After returning to the main window, click the “CHOOSE STORAGE” button and select the SD card you just plugged in.

    ![Choose Storage. The size of the SD Card may vary depending on your selection.](Screenshot%202022-12-26%20at%203.36.32%20AM.png)

### Step 1.5: Write OS to SD Card

- After choosing the storage, click the “WRITE” button on the main window.
- A pop-up warning window will appear. Click “YES” on the popup window.
- Warning: After this step, all data on the SD card will be wiped.

    ![Warning Window](Screenshot%202022-12-26%20at%203.41.31%20AM.png)

### Step 1.6: Transfer the SD Card and Power up Raspberry Pi

- Unplug the SD card reader from your computer. Gently remove the SD card from the reader and plug it into the SD card slot on the Raspberry Pi.
- Connect the keyboard, mouse, and video cable to the Raspberry Pi.
- Plug in the power supply and power on the Raspberry Pi. The power LED indicator should turn red, and the storage LED indicator should flash. You should also have a Raspberry Pi logo on the monitor.
- You should see the desktop environment on the monitor after this step.
- If you do not see the video output after 5 minutes, repeat steps 0.2 to 0.5 again. 

## Chapter 2: Setup Process

After finishing the steps described in chapter 0, you should see the video output on the monitor. For it to run for the first time, additional settings are needed to set up the Raspberry Pi, such as counties and network settings. 

### Step 2.7: Set Countries

- Select your country, keyboard layout, and language from the window.

### Step 2.8: Create User

- Create a user and password for the user. Remember to create a strong password to protect your Raspberry Pi. 

### Step 2.9: Set Up Screen

- Depending on the model of your monitor, you should change whether the screen size should be trimmed so that all content can be shown.

### Step 2.10: Select Wi-Fi Network

- Choose the wireless network from the list. If a password protects the network, you will be prompted to enter the password.

### Step 2.11: Update Software

- After connecting to the network, you will be asked whether to check for software updates. It is recommended to install new updates now, although it will take a long time. 

### Step 2.12: Setup complete

- After downloading and installing all updates, Raspberry Pi will reboot itself to apply changes.

## Chapter 3: Download Dependencies

This chapter will go through the steps to download and install all dependencies of the software.

### Step 3.13: Open Terminal

- We must interact with the operating system and its package manager using the terminal. To open the terminal, click the “Terminal” icon in the upper left corner.

    ![Terminal Icon Location.](Screenshot%202022-12-26%20at%204.58.51%20AM.png)

### Step 3.14: Refresh the Package List

- We need to download the packages from a remote server. Getting the latest package list and dependency information from the server is important. To refresh the package list, in the terminal window, enter the following command and press enter:

        sudo apt-get update

    ![Refresh Package List.](Screenshot%202022-12-26%20at%205.03.34%20AM.png)

- If the output shows that some packages can be upgraded, you can enter the following command in the terminal window to upgrade them:

        sudo apt-get upgrade

- You should restart the Raspberry Pi after a software upgrade for the changes to be applied.

### Step 3.15: Install python3-pyqt5

- PyQt5 is a binding of the Qt5 implemented by Python. It is the GUI toolkit for the software we will use later. To download the PyQt5, enter the following command in the terminal window and then press enter:

        sudo apt install python3-pyqt5

- python3-pyqt5 may have already been installed on your system, you can just ignore this step.

### Step 3.16: Install Twilio python helper library

- We use Twilio as the communication service in the project. Twilio provides a Python helper library to simplify the calling and texting process. To install the helper library, enter the following command and press enter:

        pip3 install twilio

- Since we are using the Python package manager pip3 in this process, we do not need to append sudo in front of the command.
- This command will automatically install the twilio package's dependencies for us.

### Step 3.17: Install qrcode library

- We use QR code in the GUI to help users get the information they need. The QR codes are generated in the runtime. To install the qrcode library, enter the following command and press enter:

        pip3 install qrcode

    ![Install qrcode helper library.](Screenshot%202022-12-26%20at%205.22.35%20AM.png)

- Since we only use the qrcode library in the project, we do not need to follow the orange instruction. However, if you want to use it outside the Python environment for other projects, you need to add the path to the library to the environment variables.

### Step 3.18: Install Adafruit DHT Library

- Since the DHT22 comes from the Adafruit, Adafruit also provides a helper library to read the sensors using Python. To install the helper library, run the following command in the terminal window:

        pip3 install Adafruit-DHT

### Step 3.19: Install Google Text-to-Speech Library
- When there is no internet connection, the system needs to use the speaker to call for help. Since an alarm like a fire alarm will drive people outside the building, a text-to-speech (TTS) engine is used to synthesize the alarm to sound like human speaking. The synthesized alarm will then be saved as a mp3 file. To install the TTS engine, run the following command in the terminal window:

        pip3 install gtts

### Step 3.20: Install MPG123 Library

- Once we get the synthesized alarm file, we need the MPG123 library to play the mp3 file. To install the library, run the following command in the terminal:

        sudo apt-get install mpg123

## Chapter 4: Download Software
You can download the latest version of the software using the command:

        git clone LINK_TO_GITHUB_REPO

## Chapter 5: Config Virtual Keyboard (Optional)
If you want to enter information using the touch screen only, a virtual keyboard is needed. However, the package manager of the Raspbian OS does not provide an easy way to install the virtual keyboard. Therefore, we need to compile our own virtual keyboard from the source code. To install the virtual keyboard, follow the steps in Qt virtual keyboard installation manual.
