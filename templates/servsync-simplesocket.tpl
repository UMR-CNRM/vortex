#!$python

from __future__ import print_function                  
import socket, time, sys, os

file = os.path.realpath(__file__)

address = $address

client = None
tries  = 0

while True:
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(address)
        break
    except socket.error as e:
        print("Connecting to %s failed: %s" % (address, e))

    tries += 1
    if tries == 3:
        sys.exit(1)
    else:
        time.sleep(60)
        print("Retry...")

mess = client.recv(255)
client.send("OK")
client.close()

if mess == "STEP":
    sys.exit (0)
elif mess == "STOP":
    os.unlink(file)
    sys.exit(0)
else:
    sys.exit(1)