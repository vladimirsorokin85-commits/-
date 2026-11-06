# -*- coding: utf-8 -*-
"""QR-код телефона каталога (SVG — текст, без растровых зависимостей)."""
import os

import qrcode
import qrcode.image.svg

OUT = r"D:\Проекты Дипсик\В ОКОПЕ\kilowatt\catalog\assets\img\qr-phone.svg"
PAYLOAD = "tel:+79991367142"

factory = qrcode.image.svg.SvgPathImage
img = qrcode.make(PAYLOAD, image_factory=factory, box_size=10, border=1)
img.save(OUT)
print("QR:", OUT, os.path.getsize(OUT), "байт")
