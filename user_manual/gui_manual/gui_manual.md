# Settings Manual v0.1

## Security

On the security page, you can lock or unlock the settings. Just press the "Unlock Settings" button and enter the admin passcode in the "Enter Passcode" page.

### Unlock Settings

Press "Unlock Settings" button will guide you to the passcode page. If the device does not have an admin passcode, press "Unlock Settings" button will automatically unlock all settings. When the settings are unlocked, there will be a white lock icon in the bottom right corner.

### Lock Settings

Press "Lock Settings" button will lock all the settings. The user has to enter the passcode again, if set, to access the settings. The settings will be automatically locked once the user leave the setting pages.


## Naloxone

On the Naloxone page, you can enter the new information for the Naloxone you just placed inside the safety kit. You can use the slider to set a new Naloxone max temperature, the highest permitted storing temperature for Naloxone, and a new Naloxone expiration date using the calendar widget.

### Max Temperature

The maximum permitted temperature for the Naloxone nasal spray. A typically maximum permitted temperature is 104 degrees Fahrenheit. The user can adjust the temperature by using the slider. The label next to it will show the current selected temperature. When the max temperature is reached, the system will show a red pill icon in the bottom right corner. It is also encouraged to enable SMS reporting so that the admin can be notified about the incident since there is no way to prevent the user from using the overheated Naloxone.

### Naloxone Expiration Date

The expiration date of the Naloxone in the safety kit. Once the Naloxone expired, the system will show a red bill icon in the bottom right corner. It is also encouraged to enable SMS reporting so that the admin can be notified about the incident since there is no way to prevent the user from using the expired Naloxone.

## Twilio

On the Twilio page, you can set all settings related to the Twilio service. You need to enter the Twilio phone number, the leased phone number from Twilio webpage. *You need to format the phone number with the area code.* You will also need to provide the Twilio SID, starting with "AC" and token so that we can access your account using Twilio APIs. 

### Twilio Virtual Phone Number

The leased phone number from Twilio. It is also possible to use your phone number after you set it up in the Twilio online console. *You need to format the virtual phone number with the area code.* The system will automatically check the validity of the phone number. If the entered phone number is valid, a green border will be shown around the text box. Otherwise, it will be red. The system does not prevent invalid phone numbers from being saved, although this will fail the phone call request.

### Twilio Account SID

The string identifier (SID) for your Twilio account. The length of the account SID is 34. The account SID always start with "AC". You need to enter the starting "AC" in the text box as well. A validator will run in the background to check the entered account SID. Similarly, a green border will be shown around the text box when the entered account SID is valid. Otherwise, it will be red. The system does not prevent invalid Twilio account SID from being used.

### Twilio Auth Token

The auth token from the Twilio online console. It acts as the password of your Twilio account when sending requests. 


## Emergency Call

In this setting page, you can enter the emergency call destination, address, and message. These will be used in making the emergency call. 

### Emergency Phone Number

The emergency call destination. In most cases, you should set it to 911 so that it will call the medical service when an overdoes incident happens. You can also set it to another phone number, such as the phone number of local hospitals or public safety. *You need to format the virtual phone number with the area code if you are not using 911 as the destination.* The system will automatically check the validity of the phone number. If the entered phone number is valid, a green border will be shown around the text box. Otherwise, it will be red. The system does not prevent invalid phone numbers from being saved, although this will fail the phone call request.

### Emergency Address

The installation address of the Naloxone safety kit. You should be specific about the address of the installation, including room and floor number, in the emergency address text box. You should also include the street name in the emergency address text box.

### Emergency Message

Some specific message you may want the paramedics to learn immediately, such as the route to the address. This information will be sent to the emergency service when making phone calls. 

### Important!

After entering the emergency address, you should update the emergency address in your Twilio account as well. Failure to do so will incur high costs on the bill and increase the response time of the emergency service. For details, visit [Twilio Emergency Calling](https://www.twilio.com/docs/voice/tutorials/emergency-calling-for-programmable-voice#:~:text=When%20placing%20an%20emergency%20call,for%20a%20test%20emergency%20call).

## Alarm

When it is impossible to make emergency phone calls, the system will speak the alarm message loudly using these settings.

### Alarm Message

When failed to make phone call request, the alarm message will be passed to the Google text-to-speech engine and a mp3 file will be generated. Then the generated mp3 file will be played. Therefore, it is recommended to include some meaningful words, such as "someone has overdosed" in this alarm message so that people can have a better idea of the incident.

### Voice Volume

You can use the slider to adjust the volume of the alarm. The best voice volume should make the alarm message be clear.

### Testing

You can test the current settings using the test button. You should always start with a lower voice volume before moving to higher volume. Remember to save the settings after the testing since the changes will not be automatically saved. 

## Power

In this section, you can control the power consumption of the device as well as cooling options.

### Enable Power Saving

N/A


### Active Hours
N/A

### Enable Active Cooling

Although it is not necessary to have the fan installed for the Raspberry Pi to run continuously, it is recommended to have a cooling fan set up so that the hot air can be blown out of the box quickly. By enabling this function, the cooling fan will be turned on when necessary. Otherwise, the cooling fan will always be kept off.

### Threshold Temperature

The minimum temperature to turn on the cooling fan. It is recommended to set the value to 176 degrees so that the noise can be minimized. A linear relationship between the temperature and fan speed will be used.

## Admin

In this section, you can control the behavior of the device.

### Admin Passcode

The passcode to unlock all setting sections. You can leave this empty if you want the settings to be accessible to everyone. However, leaving this empty will also nullify the naloxone passcode.

### Naloxone Passcode

The passcode to unlock the Naloxone settings. It is possible to have a different Naloxone passcode than the admin passcode.

### Allow Paramedics to Get Naloxone Passcode

If you enable this, the paramedics can retrieve the naloxone passcode by providing their phone numbers in the passcode page. Their phone numbers will also be sent to the admin so that some help can be offered by the admin. If you disable this, the paramedics can only notify the admin via SMS. The passcode retrieval requires Twilio balance.

### Admin Phone Number

The phone number of the admin. By providing this, the admin can receive SMS about the status of the device. *You need to format the admin phone number with the area code.* The system will automatically check the validity of the phone number. If the entered phone number is valid, a green border will be shown around the text box. Otherwise, it will be red. The system does not prevent invalid phone numbers from being saved, although this will fail the phone call request.

### Test Setup with Admin Phone Number

It is always a good idea to test the emergency calling during the setup process. By pressing the Call or SMS button, the admin will receive a phone call or an SMS about the message that the emergency service will hear.

### Enable SMS Report

More incidents can be reported to the admin. By enabling this, the admin can receive status update of the device. Some SMS, such as the passcode retrieval request by paramedics, cannot be disabled.

### Toggle Door Switch

It will be helpful if the admin wants to disable the door sensor when modifying the device. By pressing the "Disarm" button, the device will ignore the signal sent by the door sensor. A red door sensor icon will be shown in the bottom right corner of the screen. It is also possible to reset the device in the door open page with the door sensor disabled. Entering the settings page will always disarm the door switch, although the red icon will not be shown. You should always remember to turn on the door sensor after the work by pressing the "Arm" button.

### Exit

By pressing this button, the program will exit to the desktop.
