"""Generate TrashSpy icon: trash bin + magnifier on dark rounded square."""
from PIL import Image, ImageDraw

S = 512
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# background
d.rounded_rectangle([8, 8, S - 8, S - 8], radius=112, fill=(24, 29, 45, 255))
d.rounded_rectangle([14, 14, S - 14, S - 14], radius=106, outline=(34, 211, 238, 255), width=7)

# --- trash bin ---
cx, top_y, bot_y = 205, 178, 428
top_w, bot_w = 250, 188
d.polygon([(cx - top_w // 2, top_y), (cx + top_w // 2, top_y),
           (cx + bot_w // 2, bot_y), (cx - bot_w // 2, bot_y)],
          fill=(148, 163, 184, 255))
# right-side shading
d.polygon([(cx + 40, top_y), (cx + top_w // 2, top_y),
           (cx + bot_w // 2, bot_y), (cx + 20, bot_y)], fill=(100, 116, 139, 255))
# vertical slats
for off in (-70, -23, 24, 71):
    x_top = cx + off
    x_bot = cx + int(off * 0.72)
    d.line([(x_top, top_y + 12), (x_bot, bot_y - 12)], fill=(71, 85, 105, 255), width=13)
# rim
d.rounded_rectangle([cx - 148, 146, cx + 148, 178], radius=13, fill=(203, 213, 225, 255))
d.rounded_rectangle([cx - 148, 146, cx + 148, 178], radius=13, outline=(71, 85, 105, 255), width=4)
# lid handle
d.rounded_rectangle([cx - 46, 112, cx + 46, 146], radius=11, fill=(148, 163, 184, 255))
d.rounded_rectangle([cx - 46, 112, cx + 46, 146], radius=11, outline=(71, 85, 105, 255), width=4)

# --- magnifier (spy glass) ---
gx, gy, r = 348, 336, 96
# handle (behind glass): from edge toward bottom-right
d.line([(gx + 62, gy + 62), (452, 452)], fill=(34, 211, 238, 255), width=34)
d.ellipse([452 - 17, 452 - 17, 452 + 17, 452 + 17], fill=(34, 211, 238, 255))
# ring
d.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(34, 211, 238, 255))
d.ellipse([gx - r + 24, gy - r + 24, gx + r - 24, gy + r - 24], fill=(15, 23, 42, 255))
# glass shine
shine = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ds = ImageDraw.Draw(shine)
ds.ellipse([gx - 52, gy - 58, gx + 2, gy - 4], fill=(255, 255, 255, 110))
img = Image.alpha_composite(img, shine)

img.save("icon_preview.png")
img.save("icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                            (64, 64), (128, 128), (256, 256)])
print("icon.ico + icon_preview.png done")
