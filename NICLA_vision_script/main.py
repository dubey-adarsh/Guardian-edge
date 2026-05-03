# This code connects the NICLA vision device to a WiFi network and collects IMU data, 
# processing it in sliding windows to compute statistics and send scores to a host device 
# after running some inference on device.

# Note that the same model runs in both the NICLA visions - the helmet one and the one which is simulating the mobile device

import network, time, socket
from machine import Pin, SPI, LED
from lsm6dsox import LSM6DSOX

from ulab import numpy as np

# Connect to phone device via WiFi
SSID = "blinders"  # Network SSID
KEY = "father123"  # Network key
SAMPLE_RATE_HZ = 50  # Sample rate in Hz

# Init wlan module and connect to network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, KEY)

red_led = LED("LED_RED"); green_led = LED('LED_GREEN')
timeout = 5
while not wlan.isconnected() and timeout > 0:
    print('Trying to connect to "{:s}"...'.format(SSID))
    time.sleep_ms(1000)
    timeout -= 1

# connect to the client socket
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
PC_IP = "10.56.151.144"
PORT = 5005

# circular buffer to process the two windows of size 150 with overlap of 100
circular_buffer = np.zeros((200,6))

# indicates if the circular buffer is full
is_buffer_full = False


# return the difference buffer between the windows [head1, head1+150] and [head2, head2+150]
def get_diff_window(circular_buffer, head1, head2):
    diff_array = np.zeros((150, 6))
    for i in range(150):
        diff_array[i] = circular_buffer[(head2+i)%200] - circular_buffer[(head1+i)%200]
    return diff_array

# return circular distance between head1 and ptr
def get_dist(head1, ptr):
    if ptr >= head1:
        return ptr - head1
    else:
        return (200 - head1) + ptr

# compute the important statistics: max, min, mean for the difference buffer
def compute_stats(diff_buff):
    max_stat = np.max(diff_buff, axis=0)
    min_stat = np.min(diff_buff, axis=0)
    mean_stat = np.mean(diff_buff, axis=0)
    return max_stat, min_stat, mean_stat

# a decision tree based upon the ay_min feature which was detected to be critical via decision tree analysis
def score(ay_min):
    if ay_min <= -0.6363520100712776:
        return 1.0 # shaking
    else:
        return 0.0 # not shaking

def imu_data():
    print('Now collecting the IMU data')
    spi = SPI(5)
    cs = Pin("PF6", Pin.OUT_PP, Pin.PULL_UP)
    lsm = LSM6DSOX(spi, cs)

    sample_interval_ms = int(1000 / SAMPLE_RATE_HZ)
    
    ptr = 0
    head1 = 0
    head2 = 50
    while True:
        start_time = time.ticks_ms()
        a = lsm.accel()  # Returns (x, y, z)
        g = lsm.gyro()   # Returns (x, y, z)

        # put the new sample into the circular buffer
        circular_buffer[ptr] = np.array([a[0], a[1], a[2], g[0], g[1], g[2]]);

        
        if (get_dist(head1, ptr) == 199):
            diff_window = get_diff_window(circular_buffer, head1, head2)

            # only min_stat will be useful for our decision tree
            (max_stat, min_stat, mean_stat) = compute_stats(diff_window)

            # Add IMU device label ("B" for the other NICLA vision simulating the mobile device) into the
            # data string to be sent to the PC
            data =  "A,%f" %  (score(min_stat[1]))

            # update head1 and head2 by stride of 50            
            head1 = head2
            head2 = (head2 + 50) % 200
            client.sendto(data.encode(), (PC_IP, PORT))
        
        # increment ptr in circular fashion
        ptr = (ptr + 1) % 200

        # take care of the sampling rate logic
        elapsed = time.ticks_diff(time.ticks_ms(), start_time)
        sleep_time = sample_interval_ms - elapsed
        if sleep_time > 0:
            time.sleep_ms(sleep_time)

if wlan.isconnected() == False:
    print('Failed to connect to Wi-Fi')
    red_led.on()
    while True:
        pass
else:
    print("WiFi Connected ", wlan.ifconfig())
    green_led.on()
    imu_data()
