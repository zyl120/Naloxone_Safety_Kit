# Admin

The Admin page allows you to control the behavior of the device and access advanced settings.

## Admin Passcode

This is the passcode used to unlock all setting sections. If left empty, the settings will be accessible to everyone. However, leaving this empty will also nullify the Naloxone passcode.

## Naloxone Passcode

This is the passcode used to unlock the Naloxone settings. It is possible to have a different passcode for the Naloxone settings than the Admin passcode.

## Allow Paramedics to Get Naloxone Passcode

When this option is enabled, paramedics can retrieve the Naloxone passcode by providing their phone numbers on the passcode page. Their phone numbers will also be sent to the admin for additional support. If this option is disabled, paramedics can only notify the admin via SMS. The passcode retrieval feature requires a balance on your Twilio account.

## Admin Phone Number

This is the phone number of the admin. By providing this, the admin can receive SMS updates on the status of the device. Please make sure to include the area code when entering the phone number. The system will automatically check the validity of the phone number. If the entered phone number is valid, a green border will be shown around the text box. If it is invalid, the border will be red. The system does not prevent invalid phone numbers from being saved, but this will cause phone call requests to fail.

## Test Setup with Admin Phone Number

You can test the emergency calling during the setup process by pressing the "Call" or "SMS" button. This will send a phone call or an SMS to the admin with the message that the emergency service will hear.

## Enable SMS Reporting

By enabling this option, the admin can receive status updates of the device via SMS. Some SMS notifications, such as the passcode retrieval request by paramedics, cannot be disabled.

## Toggle Door Switch

This feature allows the admin to disable the door sensor when modifying the device. By pressing the "Disarm" button, the device will ignore signals sent by the door sensor. A red door sensor icon will be displayed in the bottom right corner of the screen. The device can also be reset with the door sensor disabled in the door open page. Entering the settings page will automatically disarm the door switch, although the red icon will not be displayed. Remember to turn on the door sensor after completing any modifications by pressing the "Arm" button.

## Exit

By pressing this button, the program will exit to the desktop.
