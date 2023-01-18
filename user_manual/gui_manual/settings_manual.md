# Settings Manual v0.1

***Always remember to save the settings after making modifications!***

## Security

The security page allows you to lock or unlock the settings on your device. To unlock the settings, press the "Unlock Settings" button and enter the admin passcode on the "Enter Passcode" page.

### Unlocking Settings

When you press the "Unlock Settings" button, you will be taken to the passcode page. If your device does not have an admin passcode set, pressing this button will automatically unlock all settings. When the settings are unlocked, you will see a white lock icon in the bottom right corner of the screen.

### Locking Settings

To lock all the settings on your device, press the "Lock Settings" button. If a passcode is set, you will need to enter it again to access the settings. Additionally, the settings will be automatically locked when you leave the settings pages.


## Naloxone

The Naloxone page allows you to update the information for the Naloxone nasal spray stored in the safety kit. You can use the slider to set a new maximum temperature for storing the Naloxone and a new expiration date using the calendar widget.

### Maximum Temperature

The maximum permitted temperature for storing the Naloxone nasal spray is typically 104 degrees Fahrenheit. You can adjust this temperature by using the slider. The label next to it will display the current temperature setting. If the maximum temperature is reached, the system will display a red pill icon in the bottom right corner of the screen. It is also recommended enabling SMS reporting so that the admin can be notified of the incident, as there is no way to prevent the use of overheated Naloxone.

### Expiration Date

This feature displays the expiration date of the Naloxone in the safety kit. Once the Naloxone has expired, the system will display a red bill icon in the bottom right corner of the screen. It is also recommended enabling SMS reporting so that the admin can be notified of the incident, as there is no way to prevent the use of expired Naloxone.

## Twilio

The Twilio page allows you to set all settings related to the Twilio service. To use the Twilio service, you will need to enter your Twilio phone number, which is a leased phone number from the Twilio website. Please make sure to include the area code when entering the phone number. You will also need to provide your Twilio Account SID (starting with "AC") and Auth Token in order to access your account using Twilio's APIs.

### Twilio Virtual Phone Number

This is the leased phone number from Twilio. It is also possible to use your own phone number after it is set up in the Twilio online console. Please make sure to include the area code when entering the virtual phone number. The system will automatically check the validity of the phone number. If the entered phone number is valid, a green border will be shown around the text box. If it is invalid, the border will be red. Please note that the system does not prevent invalid phone numbers from being saved, but this will cause phone call requests to fail.

### Twilio Account SID

The Account SID is the string identifier for your Twilio account, it is 34 characters long and always starts with "AC". Make sure to include the "AC" when entering the SID. A validator will run in the background to check the entered Account SID. If the entered SID is valid, a green border will be shown around the text box. If it is invalid, the border will be red. The system does not prevent invalid Twilio account SID from being used.

### Twilio Auth Token

The Auth Token from the Twilio online console acts as the password for your Twilio account when sending requests.


## Emergency Call

The Emergency Call page allows you to set the emergency call destination, address, and message that will be used when making an emergency call.

### Emergency Phone Number

This is the destination for the emergency call. In most cases, it should be set to 911 to call emergency medical services in the event of an overdose incident. You can also set it to another phone number, such as the phone number of a local hospital or public safety department. Please make sure to include the area code when entering the phone number if you are not using 911 as the destination. The system will automatically check the validity of the phone number. If the entered phone number is valid, a green border will be shown around the text box. If it is invalid, the border will be red. Please note that the system does not prevent invalid phone numbers from being saved, but this will cause phone call requests to fail.

### Emergency Address

This is the installation address of the Naloxone safety kit. Make sure to be specific about the address, including the room and floor number, as well as the street name.

### Emergency Message

This is a specific message that you may want paramedics to be aware of immediately, such as the route to the address. This information will be sent to the emergency service when making phone calls.

### Important!

After entering the emergency address, you must also update the emergency address in your Twilio account. Failure to do so will result in high costs on your bill and may delay the response time of the emergency service. For details, visit [Twilio Emergency Calling](https://www.twilio.com/docs/voice/tutorials/emergency-calling-for-programmable-voice#:~:text=When%20placing%20an%20emergency%20call,for%20a%20test%20emergency%20call).

## Alarm

The Alarm page allows you to set the settings for the alarm that will be used when it is impossible to make emergency phone calls.

### Alarm Message

This message will be spoken loudly by the system in case of emergency. The message will be passed to the Google text-to-speech engine, which will generate an mp3 file. This file will be played, so it is recommended to include meaningful words such as "someone has overdosed" in the message so that people have a better understanding of the incident.

### Voice Volume

You can adjust the volume of the alarm using the slider. The best volume setting should make the alarm message clear.

### Testing

You can test the current settings using the test button. It is recommended to start with a lower volume setting before increasing the volume. Remember to save the settings after testing, as changes will not be automatically saved.

## Power

The Power page allows you to control the power consumption of the device as well as cooling options.

### Enable Power Saving

This option allows you to enable or disable power saving mode on the device. When enabled, the device will use less power when not in use.

### Active Hours

This option allows you to set the hours during which the device will be actively used. During non-active hours, the device will enter power saving mode.

### Enable Active Cooling

This option allows you to enable or disable the active cooling feature on the device. It is recommended to have a cooling fan installed to quickly remove hot air from the device. When this option is enabled, the cooling fan will turn on as needed. If it is disabled, the fan will always be off.

### Threshold Temperature

This is the minimum temperature at which the cooling fan will turn on. It is recommended to set this value to 176 degrees to minimize noise. A linear relationship between temperature and fan speed will be used.

## Admin

The Admin page allows you to control the behavior of the device and access advanced settings.

### Admin Passcode

This is the passcode used to unlock all setting sections. If left empty, the settings will be accessible to everyone. However, leaving this empty will also nullify the Naloxone passcode.

### Naloxone Passcode

This is the passcode used to unlock the Naloxone settings. It is possible to have a different passcode for the Naloxone settings than the Admin passcode.

### Allow Paramedics to Get Naloxone Passcode

When this option is enabled, paramedics can retrieve the Naloxone passcode by providing their phone numbers on the passcode page. Their phone numbers will also be sent to the admin for additional support. If this option is disabled, paramedics can only notify the admin via SMS. The passcode retrieval feature requires a balance on your Twilio account.

### Admin Phone Number

This is the phone number of the admin. By providing this, the admin can receive SMS updates on the status of the device. Please make sure to include the area code when entering the phone number. The system will automatically check the validity of the phone number. If the entered phone number is valid, a green border will be shown around the text box. If it is invalid, the border will be red. The system does not prevent invalid phone numbers from being saved, but this will cause phone call requests to fail.

### Test Setup with Admin Phone Number

You can test the emergency calling during the setup process by pressing the "Call" or "SMS" button. This will send a phone call or an SMS to the admin with the message that the emergency service will hear.

### Enable SMS Report

By enabling this option, the admin can receive status updates of the device via SMS. Some SMS notifications, such as the passcode retrieval request by paramedics, cannot be disabled.

### Toggle Door Switch

This feature allows the admin to disable the door sensor when modifying the device. By pressing the "Disarm" button, the device will ignore signals sent by the door sensor. A red door sensor icon will be displayed in the bottom right corner of the screen. The device can also be reset with the door sensor disabled in the door open page. Entering the settings page will automatically disarm the door switch, although the red icon will not be displayed. Remember to turn on the door sensor after completing any modifications by pressing the "Arm" button.

### Exit

By pressing this button, the program will exit to the desktop.
