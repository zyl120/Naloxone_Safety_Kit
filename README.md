# Internet-based Naloxone Safety Kit

## Introduction

Our team seeks to address the ongoing opioid epidemic in the United States by designing and fabricating a highly-functional Internet-based naloxone safety kit. The safety kit will provide publicly accessible naloxone, so it is easily accessible in emergency situations. Additionally, the safety kit is designed to automatically call 911 when opened using the Twilio VoIP service. This will reduce the amount of time required for individuals experiencing an opioid overdose to receive medical attention. The kit is wall-mountable, so it can be deployed in almost any space. The safety kit features a sleek and intuitive touchscreen display with labeled buttons and menus for easy navigation. A printed circuit board (PCB) is used to act as an IO hub, connecting the temperature sensor, door sensor, and built-in speakers. The device is designed to store the naloxone at the optimal temperature range to ensure maximum shelf life. This is accomplished by utilizing a temperature sensor and power-efficient fan. The team utilized laser cutting to fabricate the majority of the enclosure. Locking and mounting mechanisms were also manufactured using FDM 3D printing. When the door is opened during a network outage, the device will sound an alarm. Comprehensive software settings are provided, giving users full control over the device, including access to a passcode screen that allows only authorized personnel to modify the settings. Our project offers a potential solution to reduce the number of opioid overdose deaths and improve public health and safety. Using our CAD models, circuit diagrams, source code, and instructions provided for replication, it will be easy and straightforward for others to replicate and deploy safety kits of their own.

## Structure

- The "main" folder contains the Python program and the converted Qt UI file.
- The "qt_design" folder contain the Qt creator used in designing the graphical user interface. The .ui file is converted using pyuic5 so that it can be read and used by the Python program. 
- The "scripts" folder contains installation script and systemd unit file.

## Quick Start Guide

Follow the instructions listed in the "Full Version.pdf" located in the "user_manual" folder.

## Credits
- Icons in the software come from <a target="_blank" href="https://icons8.com">Icons8</a>
