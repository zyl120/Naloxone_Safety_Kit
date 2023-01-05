# Internet-based Naloxone Safety Kit

## Introduction

This is the repo for Naloxone safety kit design project. 

## Structure

- The "archive" folder contains some testing code and little demos used during the development of the software.
- The "main" folder contains the Python program and the converted Qt UI file.
- The "qt_design" folder contain the Qt creator used in designing the graphical user interface. The .ui file is converted using pyuic so that it can be read and used by the Python program. 

## Quick Start Guide

1. First download the source code in the "main" folder and copy it to a directory on Raspberry Pi.
2. Wire the circuit according to the installation guide
3. Follow the installation guide to download necessary dependencies on the Raspberry Pi.
4. [Optional] If needed, follow the qt virtual keyboard installation guide to install the virtual keyboard for input using the touch screen.
5. Run the main program using
        
        python3 main.py
6. On first start, the program will ask the user to enter configurations. Ensure that all fields in the settings are filled by valid values before apply the changes. It could be difficult to change the values if the wrong values are used.
7. After applying the changes, the software is up and will continuously monitor the door sensor. 

## Google Drive Link

- Resources: https://docs.google.com/document/d/13WMD5f2MbXh9dzYhwJVPuzVx4vYvntCq/edit?usp=sharing&ouid=102268516998582210648&rtpof=true&sd=true
