import ubinascii
import urequests
import config


class TwilioCall:
    base_url = 'https://api.twilio.com/2010-04-01'

    def __init__(self, account_sid, auth_token):
        self.twilio_account_sid = account_sid
        self.twilio_auth = ubinascii.b2a_base64('{sid}:{token}'.format(
            sid=account_sid, token=auth_token)).strip()

    def create(self, twiml, from_, to):
        data = 'Twiml={twiml}&From={from_}&To={to}'.format(
            twiml=twiml, from_=from_.replace('+', '%2B'),
            to=to.replace('+', '%2B'))
        r = urequests.post(
            '{base_url}/Accounts/{sid}/Calls.json'.format(
                base_url=self.base_url, sid=self.twilio_account_sid),
            data=data,
            headers={'Authorization': b'Basic ' + self.twilio_auth,
                     'Content-Type': 'application/x-www-form-urlencoded'})
        print('SMS sent with status code', r.status_code)
        print('Response: ', r.text)


if __name__ == "__main__":
    response = "<Response><Say loop='0' voice='woman'>Message: Naloxone safety kit is opened. Address: 115 Hoy Rd, Ithaca, NY 14850</Say></Response>"
    safety_box = "8647138522"
    target = "5189615258"
    call = TwilioCall("AC8e97b31b36498c53c9674163a32c2f80",
                      "bc3fae0c96f301cb8712b7a9d11d7da1")
    call.create(response, safety_box, target)
