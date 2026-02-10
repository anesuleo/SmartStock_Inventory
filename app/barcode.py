import serial
import requests
import time

API_URL = "http://127.0.0.1:8002/api/inventory/scan"

ser = serial.Serial("COM8", 9600, timeout=1)
print("Waiting for barcode scans...")

while True:
    raw = ser.readline().decode(errors="ignore")

    # Strip everything except digits
    barcode = "".join(filter(str.isdigit, raw))

    if not barcode:
        continue

    print("Scanned:", barcode)

    try:
        r = requests.post(API_URL, json={"barcode": barcode}, timeout=5)

        if r.status_code == 200:
            item = r.json()
            print(
                f"{item['drug_name']} "
                f"({item['units']}) — "
                f"{item['stock_quantity']} left"
            )
        else:
            print("", r.json().get("detail", "Unknown error"))

    except requests.exceptions.RequestException as e:
        print("Connection error:", e)
        time.sleep(1)




#5060879490949
#1245452