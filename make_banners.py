from PIL import Image, ImageDraw, ImageFont
import os

BANNER_W = 1080
BANNER_H = 1350
ILLUSTRATION_H = 1080

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
LOGO_PATH = "/home/user/-/assets/logo/logo-light-on-white.png"  # чёрный логотип на белом

posts = [
    ("04-11-narodnoe-edinstvo.png", "4 ноября", "День народного единства"),
    ("07-11-parad-1941.png", "7 ноября", "День воинской славы России\nПарад 1941 года"),
    ("13-11-rhbz.png", "13 ноября", "День войск РХБЗ"),
    ("27-11-morskaya-pekhota.png", "27 ноября", "День морской пехоты"),
    ("03-12-neizvestnyy-soldat.png", "3 декабря", "День Неизвестного Солдата"),
    ("05-12-kontrnastuplenie.png", "5 декабря", "День воинской славы России\nКонтрнаступление под Москвой"),
    ("09-12-geroi-otechestva.png", "9 декабря", "День Героев Отечества"),
    ("17-12-rvsn.png", "17 декабря", "День ракетных войск\nстратегического назначения"),
    ("20-12-organy-bezopasnosti.png", "20 декабря", "День работников органов безопасности"),
    ("27-12-spasatel.png", "27 декабря", "День спасателя (МЧС России)"),
]

os.makedirs("/home/user/-/assets/banners", exist_ok=True)

logo = Image.open(LOGO_PATH).convert("RGBA")

for fname, date, event in posts:
    img = Image.open(f"/home/user/-/assets/posts/{fname}").convert("RGBA")

    # Вписываем иллюстрацию в верхний квадрат 1080x1080
    img.thumbnail((BANNER_W, ILLUSTRATION_H), Image.LANCZOS)
    canvas = Image.new("RGBA", (BANNER_W, ILLUSTRATION_H), (0, 0, 0, 255))
    x = (BANNER_W - img.width) // 2
    y = (ILLUSTRATION_H - img.height) // 2
    canvas.paste(img, (x, y), img)

    # Соберём банер 1080x1350: верх — иллюстрация, низ — чёрная полоса
    banner = Image.new("RGBA", (BANNER_W, BANNER_H), (0, 0, 0, 255))
    banner.paste(canvas, (0, 0))

    draw = ImageDraw.Draw(banner)

    # Логотип в левом нижнем углу белым квадратом
    logo_size = 140
    logo_resized = logo.resize((logo_size, logo_size), Image.LANCZOS)
    draw.rectangle([30, ILLUSTRATION_H + 30, 30 + logo_size, ILLUSTRATION_H + 30 + logo_size], fill=(255, 255, 255, 255))
    banner.paste(logo_resized, (30, ILLUSTRATION_H + 30), logo_resized)

    # Текст справа от логотипа
    text_x = 30 + logo_size + 30
    text_y = ILLUSTRATION_H + 45

    f_date = ImageFont.truetype(FONT_BOLD, 60)
    f_event = ImageFont.truetype(FONT_BOLD, 40)

    draw.text((text_x, text_y), date, font=f_date, fill=(255, 255, 255, 255))

    y_offset = text_y + 80
    for line in event.split("\n"):
        draw.text((text_x, y_offset), line, font=f_event, fill=(220, 220, 220, 255))
        y_offset += 60

    out_path = f"/home/user/-/assets/banners/banner_{fname}"
    banner.convert("RGB").save(out_path, "PNG")
    print("Saved:", out_path)

print("Готово. Все банеры в /home/user/-/assets/banners/")
