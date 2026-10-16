"""Generate Doro's PNG icons from a simple vector description (no design tool needed)."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "icons"
OUT.mkdir(exist_ok=True)
BG = (228, 87, 62)      # focus coral
FG = (255, 255, 255)

def render(size: int, maskable: bool = False, bg_radius_ratio: float = 0.22) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if maskable:
        d.rectangle([0, 0, s, s], fill=BG)
    else:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * bg_radius_ratio), fill=BG)
    # progress ring: a 300° arc with a gap at the top-right, like the app's ring at ~83%
    pad = s * (0.30 if maskable else 0.24)
    width = int(s * 0.11)
    box = [pad, pad, s - pad, s - pad]
    d.arc(box, start=-90, end=210, fill=FG, width=width)
    # round the arc ends
    import math
    r = (s - 2 * pad) / 2
    cx = cy = s / 2
    for ang in (-90, 210):
        x = cx + (r - width / 2) * math.cos(math.radians(ang))
        y = cy + (r - width / 2) * math.sin(math.radians(ang))
        d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=FG)
    return img.resize((size, size), Image.LANCZOS)

render(192).save(OUT / "icon-192.png")
render(512).save(OUT / "icon-512.png")
render(512, maskable=True).save(OUT / "icon-maskable-512.png")
render(180).save(OUT / "apple-touch-icon.png")

# Open Graph image 1200x630
og = Image.new("RGB", (1200, 630), (244, 241, 234))
icon = render(200)
og.paste(icon, (500, 120), icon)
d = ImageDraw.Draw(og)
from PIL import ImageFont
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
except OSError:
    font = small = ImageFont.load_default()
def center(text, y, f, fill):
    w = d.textlength(text, font=f)
    d.text(((1200 - w) / 2, y), text, font=f, fill=fill)
center("doro", 350, font, (29, 28, 26))
center("Open a tab. Press Space. Focus.", 440, small, (94, 91, 85))
center("No account · No tracking · Works offline", 490, small, (154, 150, 142))
og.save(OUT / "og.png", optimize=True)
print("icons written to", OUT)
