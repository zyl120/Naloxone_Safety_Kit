# Internet-based Naloxone Safety Kit

## Introduction

The United States is currently facing an opioid epidemic, with an increasing number of people dying every year due to opioid overdoses. Naloxone is a life-saving drug that can be administered to overdose victims, but it takes time for emergency services to arrive after 911 has been called, which can often be too late. This has led to a need for publicly accessible naloxone to be made available, which is where the proposal for a naloxone safety kit comes in.

The proposed kit aims to provide safe, reliable, and temperature-controlled storage of publicly accessible naloxone, which, when opened, will automatically dial 911 and request medical emergency services. The kit could help minimize deaths due to opioid overdoses by reducing the time it takes for emergency services to reach overdose victims.

Traditionally, naloxone is given in the form of intramuscular injection by professionals. However, in 2015, the first naloxone nasal spray, the Narcan Nasal Spray, was approved by the FDA, making it easier for anyone to provide first aid in case of an overdose. Some organizations, like NaloxBox, have introduced naloxone safety kits to the market after the approval of the nasal spray. However, these kits cannot call emergency services automatically when opened, instead triggering a siren. Moreover, their price is too high to be deployed massively, with each kit costing around $250 to $300 without naloxone.

An internet-connected enclosure for a naloxone safety kit will solve these problems, automatically dialing 911 when opened to report the location of the incident. Such a device will be of lifesaving practical utility in places where recreational drugs are consumed, and the enclosure will be designed to be an artistic reminder of the opioid epidemic. The proposed kit aims to reduce the cost of the whole safety kit while achieving these improvements.

## Structure

- The "main" folder contains the Python program and the converted Qt UI file.
- The "qt_design" folder contain the Qt creator used in designing the graphical user interface. The .ui file is converted using pyuic5 so that it can be read and used by the Python program. 

## Quick Start Guide

1. First download the source code in the "main" folder and copy it to a directory on Raspberry Pi.
2. Wire the circuit according to the installation guide
3. Use the installation script "install.py" to download and deploy the software on the Raspberry Pi automatically.
4. Run the main program using
        
        python3 main.py
5. On first start, the program will ask the user to enter configurations. Ensure that all fields in the settings are filled by valid values before apply the changes. It could be difficult to change the values if the wrong values are used.
6. After applying the changes, the software is up and will continuously monitor the door sensor. 

## Google Drive Link

- Resources: https://docs.google.com/document/d/13WMD5f2MbXh9dzYhwJVPuzVx4vYvntCq/edit?usp=sharing&ouid=102268516998582210648&rtpof=true&sd=true

## Credits
- Icons in the software come from <a target="_blank" href="https://icons8.com">Icons8</a>
