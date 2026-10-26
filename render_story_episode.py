"""Offline mystery reel with Piper neural narration, Pillow, and FFmpeg."""
import math
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import argparse
import json
import re
import textwrap

parser = argparse.ArgumentParser(description="Render an episode JSON using animated visuals and Piper TTS")
parser.add_argument("--episode", default="story/current_episode.json")
args = parser.parse_args()
episode_path = Path(args.episode)
if not episode_path.exists():
    raise SystemExit(f"Episode JSON is missing: {episode_path}")
episode = json.loads(episode_path.read_text(encoding="utf-8"))
for required in ("title", "episode", "total_episodes", "narration", "question"):
    if required not in episode:
        raise SystemExit(f"Episode JSON missing field: {required}")
if not episode["narration"] or not isinstance(episode["narration"], list):
    raise SystemExit("Episode narration must be a nonempty list")

W, H, FPS = 540, 960, 20
OUT = Path('output') / f"mystery_episode_{episode['episode']:02d}.mp4"
OUT.parent.mkdir(exist_ok=True)
FONT_DIR = '/usr/share/fonts/truetype/dejavu'

def short_lines(text, width=22):
    text = re.sub(r"\s+", " ", text).strip()
    # Prefer concise on-screen beats rather than copying paragraphs into a tiny screen.
    lines = textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1].rstrip(' .') + '...'
    return [line.upper() for line in lines]

SCENES = []
now = 0
for i, dialogue in enumerate(episode['narration']):
    if not isinstance(dialogue, str) or not dialogue.strip():
        raise SystemExit(f"Narration line {i+1} must be nonempty text")
    words = len(dialogue.split())
    scene_duration = max(7, min(17, round(words/2.25 + 2)))
    SCENES.append((now, now+scene_duration, dialogue.strip(), short_lines(dialogue)))
    now += scene_duration
question = episode['question']
if question:
    vote_text = question + " Comment yes or no to decide what happens next."
    SCENES.append((now, now+9, vote_text, short_lines(question, width=23)))
    now += 9
else:
    SCENES.append((now, now+7, "The mystery is solved. The end.", ["THE MYSTERY IS SOLVED", "THE END"]))
    now += 7
DURATION = now
IS_FINALE = not bool(question)


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
    gap = int(max(0,min(67,(t-DURATION*0.65)*15)))
    d.rectangle((x0+12,306,x0+172,676),fill='#020408')
    d.rectangle((x0+12+gap,306,x0+92,676),fill='#263345')
    d.rectangle((x0+92,x0 and 306,x0+172-gap,676),fill='#263345') if gap < 68 else None
    d.line((x0+92,306,x0+92,675),fill='#607087',width=3) if gap<5 else None
    center(d,'4' if t>DURATION*0.5 else '3', 328, 43,'#ff738c',True)
    if t > DURATION*0.65:
        opacity = min(1,(t-DURATION*0.65)/2)
        shadow='#010204'
        sx=x0+86
        d.ellipse((sx-20,454,sx+20,498),fill=shadow)
        d.polygon([(sx-14,493),(sx+14,493),(sx+27,631),(sx-24,631)],fill=shadow)
    if t < DURATION - (7 if IS_FINALE else 9):
        xpos=160+min(t/max(1,DURATION*0.6),1)*57
        person(d,xpos,654, t*2.4 if t<DURATION*0.55 else 0)
        # light beam grows toward door
        d.polygon([(xpos+26,603),(x0+12,529),(x0+12,616)], fill='#22283a')
    # atmospheric rain lines and flickering lights
    for j in range(22):
        rx=(j*83+17)%W
        ry=(j*169+int(t*85))%690+95
        d.line((rx,ry,rx-3,ry+17),fill='#263244',width=2)
    d.rounded_rectangle((22,28,518,110),radius=16,fill='#151e2c')
    center(d, episode['title'].upper()[:29],43,25,bold=True)
    center(d, f"EPISODE {episode['episode']:02d}/{episode['total_episodes']:02d}  •  VOTE THE MYSTERY",88,14,color='#b2bacb')
    d.rounded_rectangle((18,735,522,927),radius=20,fill='#111b2b',outline='#354154',width=2)
    lines=SCENES[scene][3]
    is_choice = (scene == len(SCENES) - 1)
    line_size = 24 if max(map(len, lines), default=0) > 22 else 27
    top_y = 778 if len(lines) >= 3 else 797
    for k, line in enumerate(lines):
        center(d, line, top_y+39*k, line_size, color=('#ff8098' if k==len(lines)-1 else '#f4f5f8'), bold=True)
    if is_choice:
        center(d, 'THE END' if IS_FINALE else 'COMMENT YES OR NO', 894, 21, color='#ff8098', bold=True)
    else:
        center(d,'Listen closely...',895,16,color='#9eacc4')
    d.rounded_rectangle((22,942,518,950),radius=4,fill='#333b4c')
    d.rounded_rectangle((22,942,22+int(496*t/DURATION),950),radius=4,fill='#ff728b')
    return im

def run(cmd):
    subprocess.run(cmd,check=True)

# Generate a separate Piper neural narration clip for each scene.
# The voice model is downloaded by the GitHub workflow.
import wave
from piper import PiperVoice

voice = PiperVoice.load('en_US-lessac-medium.onnx')
clips=[]
for i, (start,end,dialogue,_) in enumerate(SCENES):
    clip=str(OUT.parent / f'voice_scene_{i}.wav')
    with wave.open(clip, 'wb') as audio:
        voice.synthesize_wav(dialogue, audio)
    with wave.open(clip, 'rb') as audio:
        clip_duration = audio.getnframes() / audio.getframerate()
    scene_duration = end-start
    if clip_duration > scene_duration - 0.3:
        print(f'WARNING: Scene {i+1}: speech duration {clip_duration:.1f}s '
              f'exceeds available {scene_duration:.1f}s; adjust story timing later.', flush=True)
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

print('Mixing Piper narration and atmospheric sound...',flush=True)
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(OUT.parent/'silent.mp4')]
for _,clip in clips: cmd.extend(['-i',clip])
# Low atmospheric tone, with narration delayed to its matching scene.
filters=[f'sine=frequency=67:sample_rate=22050:duration={DURATION},volume=0.035[amb]']
for idx,(start,_) in enumerate(clips, start=1):
    filters.append(f'[{idx}:a]aformat=sample_rates=22050:channel_layouts=mono,adelay={start*1000}:all=1,volume=1.15[v{idx}]')
filters.append('[amb]'+''.join(f'[v{i}]' for i in range(1,len(clips)+1))+
               f'amix=inputs={len(clips)+1}:duration=longest:normalize=0,atrim=0:{DURATION}[aout]')
cmd.extend(['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[aout]',
            '-c:v','copy','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(OUT)])
run(cmd)
print('Created:',OUT,flush=True)
print('Episode JSON:', episode_path, '| total duration:', DURATION, 'seconds', flush=True)
