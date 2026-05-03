import socket
import csv
import os
from datetime import datetime
import time
 
# -----------------------------
# CONFIG
# -----------------------------
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
# -----------------------------

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
 
print(f"Listening on UDP port {UDP_PORT}")

activity_map = {0: "falling", 1: "jerking", 2: "riding", 3: "Can't classify!!"}

print("Nicla Vision: Starting Real-time Inference...")

recieved_from_A = False
recieved_from_B = False

try:
    while True:
        # recieve data from NICLA vision device A or B
        data, addr = sock.recvfrom(1024)
        decoded = data.decode().strip()
        row = decoded.split(",")
        print(row)
        device = row[0]

        # only bool value needed to know if the device is shaking or not
        is_shaking = float(row[1]) == 1.0

        if device == "A":
            recieved_from_A = True
            A_is_shaking = is_shaking

        elif device == "B":
            recieved_from_B = True
            B_is_shaking = is_shaking

        # a little boolean logic to combine the two device inferences into a 
        # final activity prediction
        predicted_activity = "Can't classify!!"
        if recieved_from_A and recieved_from_B:
            if A_is_shaking and B_is_shaking:
                predicted_activity = "falling"
            elif A_is_shaking and not(B_is_shaking):
                predicted_activity = "jerking"
            elif not(A_is_shaking) and not(B_is_shaking):
                predicted_activity = "riding"
            
            print("data", row)
            print("prediction: ", predicted_activity)
            recieved_from_A = False
            recieved_from_B = False

except KeyboardInterrupt:
    print("\nStopped. File saved.")
 
sock.close()