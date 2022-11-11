import os
from time import sleep

def ping():
    hostname = "https://api.twilio.com"  # ping twilio directly
    response = os.system("ping -c 1 " + hostname)

    # and then check the response...
    if response == 0:
        #print(hostname, 'is up!')
        return True
    else:
        #print(hostname, 'is down!')
        return False


def server_connection(shm_c):
    while True:
        server_status = ping()
        if(not shm_c.buf[8]):
            shm_c.buf[8] = True # critical section for server status
            shm_c.buf[9] = server_status
            shm_c.buf[8] = False # critical section ends for server status
        sleep(3600)
