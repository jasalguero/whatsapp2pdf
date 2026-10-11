"""Build the synthetic "Weekend hike" demo export and PDF used for the docs screenshots.

All names, messages and images are made up. Run: python scripts/make_demo.py
then: pdftoppm -png -r 110 demo.pdf page
"""
import random
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from whatsapp2pdf import convert, LayoutConfig

def scene(path, sky, ground, sun):
    w, h = 1600, 1200
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        c = tuple(int(sky[0][i] * (1 - t) + sky[1][i] * t) for i in range(3))
        d.line([(0, y), (w, y)], fill=c)
    d.ellipse([sun[0]-90, sun[1]-90, sun[0]+90, sun[1]+90], fill=(255, 236, 180))
    random.seed(len(path))
    pts = [(0, h)] + [(x, int(h*0.55 + random.randint(-120, 60))) for x in range(0, w+200, 200)] + [(w, h)]
    d.polygon(pts, fill=ground[0])
    pts2 = [(0, h)] + [(x, int(h*0.75 + random.randint(-60, 40))) for x in range(0, w+160, 160)] + [(w, h)]
    d.polygon(pts2, fill=ground[1])
    im.filter(ImageFilter.GaussianBlur(2)).save(path, quality=88)

scene("IMG-20260314-WA0001.jpg", ((120,170,230),(250,210,170)), ((70,110,90),(40,80,60)), (1200, 380))
scene("IMG-20260315-WA0002.jpg", ((40,60,120),(240,140,110)), ((60,70,100),(30,40,70)), (400, 700))
chat = """14/03/26, 09:58 - Messages and calls are end-to-end encrypted. Only people in this chat can read, listen to, or share them.
14/03/26, 09:58 - Maya created group "Weekend hike"
14/03/26, 09:59 - Maya: Morning everyone! Still on for the ridge trail? 🥾
14/03/26, 10:00 - Leo: Yes! I'll bring the thermos ☕
14/03/26, 10:00 - Leo: And snacks
14/03/26, 10:01 - Alex: Count me in. Meeting at the car park at 10:30?
14/03/26, 10:02 - Sam: Running 10 minutes late, sorry!
Start without me if you need to.
14/03/26, 10:15 - Maya: IMG-20260314-WA0001.jpg (file attached)
14/03/26, 10:15 - Maya: The view from the first lookout already 😍
14/03/26, 10:16 - Alex: 😍😍
14/03/26, 10:20 - Leo: trail-map.pdf (file attached)
14/03/26, 10:21 - Sam: <Media omitted>
15/03/26, 18:39 - Alex: Home safe. What a day!
15/03/26, 18:40 - Alex: IMG-20260315-WA0002.jpg (file attached)
15/03/26, 18:41 - Maya: That sunset photo is going straight on the fridge
15/03/26, 18:42 - Leo: We walked about 18 kilometres, saw two deer, got slightly lost near the second ridge, and still made it back before sunset. Same time next month?
15/03/26, 18:43 - Sam: 👍
"""
with zipfile.ZipFile("WhatsApp Chat - Weekend hike.zip", "w") as z:
    z.writestr("_chat.txt", chat)
    z.write("IMG-20260314-WA0001.jpg"); z.write("IMG-20260315-WA0002.jpg")
    z.writestr("trail-map.pdf", "%PDF-1.4\n")
r = convert("WhatsApp Chat - Weekend hike.zip", "demo.pdf", outgoing="Alex", config=LayoutConfig(page_size="A5"))
print(r)
