#*****************************
#qr_gererator.py   ver 04--
#*****************************

import qrcode, os

def generate_qr(data, name):
    os.makedirs("assets/qr_codes", exist_ok=True)
    img = qrcode.make(data)
    path = os.path.join("assets/qr_codes", f"{name}.png")
    img.save(path)
    return path