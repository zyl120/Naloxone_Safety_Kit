# Twilio

The Twilio page allows you to set all settings related to the Twilio service. To use the Twilio service, you will need to enter your Twilio phone number, which is a leased phone number from the Twilio website. Please make sure to include the area code when entering the phone number. You will also need to provide your Twilio Account SID (starting with "AC") and Auth Token in order to access your account using Twilio's APIs.

## Twilio Virtual Phone Number

This is the leased phone number from Twilio. It is also possible to use your own phone number after it is set up in the Twilio online console. Please make sure to include the area code when entering the virtual phone number. The system will automatically check the validity of the phone number. If the entered phone number is valid, a green border will be shown around the text box. If it is invalid, the border will be red. Please note that the system does not prevent invalid phone numbers from being saved, but this will cause phone call requests to fail.

## Twilio Account SID

The Account SID is the string identifier for your Twilio account, it is 34 characters long and always starts with "AC". Make sure to include the "AC" when entering the SID. A validator will run in the background to check the entered Account SID. If the entered SID is valid, a green border will be shown around the text box. If it is invalid, the border will be red. The system does not prevent invalid Twilio account SID from being used.

## Twilio Auth Token

The Auth Token from the Twilio online console acts as the password for your Twilio account when sending requests.
