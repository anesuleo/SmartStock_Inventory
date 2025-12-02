import serial
import requests

API_URL = "http://127.0.0.1:8000/api/inventory/scan"

ser = serial.Serial('COM6', 9600, timeout=1)
print("Waiting for scans...")

while True:
    data = ser.readline().decode().strip()
    if data:
        print("Scanned:", data)
        try:
            r = requests.post(API_URL, json={"barcode": data})
            if r.status_code == 200:
                item = r.json()
                print(f"{item['drug_name']} ({item['units']}) — {item['stock_quantity']} left")
            else:
                print("Error:", r.json().get("detail", "Unknown error"))
        except requests.exceptions.RequestException as e:
            print("Connection error:", e)



#5060879490949
#1245452