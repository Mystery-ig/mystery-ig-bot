"""Offline narrated mystery prototype. Uses Pillow, FFmpeg, and eSpeak NG."""
import math
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DURATION = 540, 960, 20, 39
OUT = Path('output/mystery_episode_02.mp4')
OUT.parent.mkdir(exist_ok=True)
FONT_DIR = '/usr/share/fonts/truetype/dejavu'

SCENES = [
    (0, 6, 'At 2:14 AM, Mia received a voicemail from herself.', ['A VOICEMAIL', 'FROM HERSELF']),
    (6, 12, 'The recording said: Whatever you do, do not enter floor four.', ['DO NOT ENTER', 'FLOOR FOUR']),
    (12, 19, 'There was only one problem. Her building had no fourth floor.', ['THERE IS NO', 'FOURTH FLOOR']),
    (19, 26, 'Then the elevator display flickered. Three. Four.', ['THE DISPLAY', 'CHANGED TO 4']),
    (26, 32, 'The doors slowly opened. A voice whispered her name.', ['SOMEONE INSIDE', 'WHISPERED: MIA']),
    (32, 39, 'Should Mia enter the elevator? Vote yes or no in the comments.', ['SHOULD MIA', 'ENTER?']),
]

def font(size, bold=False):
    return ImageFont.truetype(f'{FONT_DIR}/DejaVuSans-{"Bold" if bold else ""}.ttf'.replace('Sans-.','Sans.'), size)

def center(draw, msg, y, size, color='#f3f5fa', bold=False):
    f = font(size, bold)
    bounds = draw.textbbox((0, 0), msg, font=f)
    draw.text(((W-(bounds[2]-bounds[0]))/2, y), msg, fill=color, font=f)

def person(draw, x, y, walk=0, face=1):
    c = '#E8EBF4'
    draw.ellipse((x-19, y-138, x+19, y-100), outline=c, width=5)
    draw.line((x,y-100,x+6,y-35), fill=c, width=6)
    swing = 16*math.sin(walk)
    draw.line((x+6,y-35,x-22+swing,y+22), fill=c, width=5)
    draw.line((x+6,y-35,x+25-swing,y+22), fill=c, width=5)
    draw.line((x+2,y-80,x-29-swing*.4,y-39), fill=c, width=5)
    draw.line((x+2,y-80,x+24+swing*.4,y-47), fill=c, width=5)
    # flashlight point and beam
    if face:
        draw.ellipse((x+20,y-52,x+29,y-43),fill='#ffdc83')

def get_scene(t):
    for i, (start, end, _, _) in enumerate(SCENES):
        if start <= t < end: return i
    return len(SCENES)-1

def frame(t):
    scene = get_scene(t)
    im = Image.new('RGB', (W,H), '#090d16')
    d = ImageDraw.Draw(im)
    # camera drifts toward the elevator as tension mounts
    drift = int(8*math.sin(t*.3))
    d.polygon([(0,170),(W,170),(310+drift,395),(225+drift,395)], fill='#111927')
    d.polygon([(0,800),(W,800),(310+drift,540),(225+drift,540)], fill='#151b27')
    for x in (0,W):
        d.line((x,200,270+drift,400),fill='#344252',width=3)
        d.line((x,780,270+drift,550),fill='#344252',width=3)
    # ominous door
    x0=295+drift
    intensity=int(52+35*math.sin(t*2))
    d.rectangle((x0,292,x0+184,691),fill='#111723',outline=(intensity+65,32,52),width=5)
    gap = int(max(0,min(67,(t-25)*15)))
    d.rectangle((x0+12,306,x0+172,676),fill='#020408')
    d.rectangle((x0+12+gap,306,x0+92,676),fill='#263345')
    d.rectangle((x0+92,x0 and 306,x0+172-gap,676),fill='#263345') if gap < 68 else None
    d.line((x0+92,306,x0+92,675),fill='#607087',width=3) if gap<5 else None
    center(d,'4' if t>20 else '3', 328, 43,'#ff738c',True)
    if t>27:
        opacity = min(1,(t-27)/2)
        shadow='#010204'
        sx=x0+86
        d.ellipse((sx-20,454,sx+20,498),fill=shadow)
        d.polygon([(sx-14,493),(sx+14,493),(sx+27,631),(sx-24,631)],fill=shadow)
    if t<32:
        xpos=160+min(t/23,1)*57
        person(d,xpos,654, t*2.4 if t<22 else 0)
        # light beam grows toward door
        d.polygon([(xpos+26,603),(x0+12,529),(x0+12,616)], fill='#22283a')
    # atmospheric rain lines and flickering lights
    for j in range(22):
        rx=(j*83+17)%W
        ry=(j*169+int(t*85))%690+95
        d.line((rx,ry,rx-3,ry+17),fill='#263244',width=2)
    d.rounded_rectangle((22,28,518,110),radius=16,fill='#151e2c')
    center(d,'THE MISSING FLOOR',43,29,bold=True)
    center(d,'EPISODE 01  •  VOTE THE MYSTERY',88,14,color='#b2bacb')
    d.rounded_rectangle((18,735,522,927),radius=20,fill='#111b2b',outline='#354154',width=2)
    lines=SCENES[scene][3]
    if scene==5:
        center(d,lines[0],772,36,bold=True)
        center(d,lines[1],815,43,color='#ff7690',bold=True)
        center(d,'COMMENT YES OR NO',883,23,color='#f4f5f8',bold=True)
    else:
        center(d,lines[0],783,29,bold=True)
        center(d,lines[1],831,29,color='#ff8098',bold=True)
        center(d,'Listen closely...',895,16,color='#9eacc4')
    d.rounded_rectangle((22,942,518,950),radius=4,fill='#333b4c')
    d.rounded_rectangle((22,942,22+int(496*t/DURATION),950),radius=4,fill='#ff728b')
    return im

def run(cmd):
    subprocess.run(cmd,check=True)

# TTS clips generated automatically using a free voice engine, timed to the animation.
clips=[]
for i, (start,end,dialogue,_) in enumerate(SCENES):
    clip=str(OUT.parent / f'voice_{i}.wav')
    run(['espeak-ng','-v','en-us','-s','145','-p','38','-a','170','-w',clip,dialogue])
    clips.append((start,clip))

print('Rendering animated frames...',flush=True)
raw_cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
         '-s',f'{W}x{H}','-r',str(FPS),'-i','-','-t',str(DURATION),'-c:v','libx264',
         '-preset','veryfast','-crf','26','-pix_fmt','yuv420p',str(OUT.parent/'silent.mp4')]
with subprocess.Popen(raw_cmd,stdin=subprocess.PIPE) as proc:
    try:
        for n in range(FPS*DURATION):
            proc.stdin.write(frame(n/FPS).tobytes())
    except BrokenPipeError:
        raise RuntimeError('FFmpeg video rendering ended unexpectedly')
    proc.stdin.close()
    if proc.wait()!=0: raise RuntimeError('FFmpeg video rendering failed')

print('Mixing narration and atmospheric sound...',flush=True)
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(OUT.parent/'silent.mp4')]
for _,clip in clips: cmd.extend(['-i',clip])
# Low atmospheric tone, with narration delayed to its matching scene.
filters=['sine=frequency=67:sample_rate=22050:duration=39,volume=0.035[amb]']
for idx,(start,_) in enumerate(clips, start=1):
    filters.append(f'[{idx}:a]aformat=sample_rates=22050:channel_layouts=mono,adelay={start*1000}:all=1,volume=1.6[v{idx}]')
filters.append('[amb]'+''.join(f'[v{i}]' for i in range(1,len(clips)+1))+
               f'amix=inputs={len(clips)+1}:duration=longest:normalize=0,atrim=0:39[aout]')
cmd.extend(['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[aout]',
            '-c:v','copy','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(OUT)])
run(cmd)
print('Created:',OUT,flush=True)

