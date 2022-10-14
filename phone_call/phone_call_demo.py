import os
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Say

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
resonse = VoiceResponse()
location = "115 Hoy Rd, Ithaca, NY 14850"
resonse.say("Hello World from " + location + ". ", voice="woman", loop=0)
print(resonse)

client = Client(account_sid, auth_token)
call = client.calls.create(
    twiml=resonse,
    to='+15189615258',
    from_='+18647138522'
)

print(call.sid)
