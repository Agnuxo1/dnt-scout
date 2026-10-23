"""A poster frame for the README: the result scene, rendered clean, with a play badge."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
V = Path("/home/ai/proyectos/dnt-scout/video")
sys.path.insert(0, str(V / "tools"))
import vis
nar = json.loads((V / "narration.json").read_text())
dur = nar["scenes"]["S4"]["duration"] + 0.55
img = vis.scene_s4(dur * 0.92, dur).convert("RGB")      # late enough that everything is revealed

# a restrained play badge, bottom-left, out of the way of the figure
d = ImageDraw.Draw(img, "RGBA")
cx, cy, r = 150, 960, 46
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(14, 111, 99, 235))
d.polygon([(cx - 14, cy - 22), (cx - 14, cy + 22), (cx + 24, cy)], fill=(255, 255, 255, 255))
d.text((cx + r + 26, cy - 30), "Watch the film", font=vis.font(34, True), fill=vis.INK)
d.text((cx + r + 26, cy + 8), "3 min 17 s  ·  English, subtitled", font=vis.font(22),
       fill=vis.MUTED)
img.save(V.parent / "results/figs/08_film_poster.png")
print("wrote results/figs/08_film_poster.png", img.size)
