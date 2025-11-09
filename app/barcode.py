import serial

ser = serial.Serial('COM9', 9600, timeout=1)

print("Waiting for scans...")

while True:
    data = ser.readline().decode().strip()
    if data:
        print("Scanned:", data)