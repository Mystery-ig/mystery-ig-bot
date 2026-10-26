"""Render a simple original animated mystery Reel (prototype; no Instagram upload)."""
import math
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SECONDS = 540, 960, 24, 32
OUT = 'output/mystery_episode_01.mp4'
os.makedirs('output', exist_ok=True)

def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/' + name, size)

def centered(draw, message, y, size=28, fill='white', bold=False):
    f = font(size, bold)
    bb = draw.textbbox((0, 0), message, font=f)
    draw.text(((W - (bb[2] - bb[0])) / 2, y), message, font=f, fill=fill)

def person(draw, x, y, sway=0, color='#E9EDF6'):
    # head + animated torso/limbs
    draw.ellipse((x-20, y-140, x+20, y-100), outline=color, width=5)
    draw.line((x, y-98, x+sway, y-28), fill=color, width=6)
    draw.line((x+sway, y-28, x-25, y+27), fill=color, width=5)
    draw.line((x+sway, y-28, x+25, y+27), fill=color, width=5)
    draw.line((x, y-81, x-40, y-41), fill=color, width=5)
    draw.line((x, y-81, x+37, y-45), fill=color, width=5)

def frame(t):
    im = Image.new('RGB', (W,H), '#0B101B')
    d = ImageDraw.Draw(im)
    # hallway perspective
    d.line((0, 180, W//2, 390), fill='#263344', width=3)
    d.line((W, 180, W//2, 390), fill='#263344', width=3)
    d.line((0, 790, W//2, 560), fill='#263344', width=3)
    d.line((W, 790, W//2, 560), fill='#263344', width=3)
    # ominous elevator doorway, slight pulsing glow
    glow = int(28 + 17 * (1 + math.sin(t*2.1)))
    d.rectangle((320, 320, 485, 690), outline=(glow, 65, 92), width=6)
    d.rectangle((329, 329, 476, 681), fill='#111521', outline='#6F243F', width=3)
    d.line((403, 330, 403, 680), fill='#394354', width=3)
    centered(d, '4', 365, 33, '#FB647B', True)
    # shadow moving only after the elevator opens
    if t >= 18:
        d.ellipse((400, 450, 434, 488), fill='#020408')
        d.rectangle((407, 487, 427, 595), fill='#020408')
    sway = round(math.sin(t*3)*4)
    person(d, 180 + (min(t,17)/17)*50, 610, sway)
    # dark title/header and subtitle zone
    d.rounded_rectangle((20, 30, 520, 112), radius=16, fill='#141D2B')
    centered(d, 'THE MISSING FLOOR', 43, 30, '#F9FAFF', True)
    centered(d, 'EPISODE 01', 86, 16, '#91A6BB')
    d.rounded_rectangle((24, 736, 516, 916), radius=20, fill='#141D2B')
    if t < 5:
        lines = ['At 2:14 AM, Mia received', 'a voicemail from herself.']
    elif t < 11:
        lines = ['"Whatever you do...', 'do not enter Floor 4."']
    elif t < 18:
        lines = ['Her building has no fourth floor.', 'Then the elevator lit up: 4.']
    elif t < 25:
        lines = ['The doors opened.', 'A voice inside whispered: "Mia."']
    else:
        lines = ['SHOULD MIA ENTER?', 'COMMENT YES OR NO']
    for i, line in enumerate(lines):
        centered(d, line, 772+i*43, 23 if t<25 else 27,
                 '#FAFAFC' if i==0 else '#FB647B', i == 0 or t>=25)
    # progress bar
    d.rounded_rectangle((24, 932, 516, 940), radius=4, fill='#263344')
    d.rounded_rectangle((24, 932, 24+int(492*t/SECONDS), 940), radius=4, fill='#FB647B')
    return im

command = [
    'ffmpeg','-hide_banner','-loglevel','error','-y',
    '-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}',
    '-r',str(FPS),'-i','-',
    '-c:v','libx264','-preset','veryfast','-crf','23',
    '-pix_fmt','yuv420p','-movflags','+faststart',OUT
]
print('Rendering demo video...', flush=True)
with subprocess.Popen(command, stdin=subprocess.PIPE) as proc:
    for n in range(FPS * SECONDS):
        proc.stdin.write(frame(n/FPS).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit('FFmpeg failed')
print('Created', OUT)
