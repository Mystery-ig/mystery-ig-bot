"""Zero-dependency prototype: coherent mystery arcs with audience choices.

This is a structured branching story engine, not a generative language model.
Future integration will convert episode scene text into voice and animation.
"""
import argparse
import json
import random
from pathlib import Path

ROOT = Path('story')
STATE = ROOT / 'state.json'

MYSTERIES = [
    {'title': 'The Missing Floor', 'lead': 'Mia', 'location': 'the old apartment building',
     'warning': 'never enter the fourth floor', 'clue': 'a brass key marked 404',
     'secret': 'The fourth floor was erased from building records after a fatal experiment, but its elevator still runs.',
     'suspect': 'the night caretaker'},
    {'title': 'The Last Train', 'lead': 'Eli', 'location': 'the abandoned train station',
     'warning': 'never board the train after midnight', 'clue': 'a ticket dated twenty years ago',
     'secret': 'The midnight train is replaying the night a passenger disappeared; someone changed the timetable.',
     'suspect': 'the station attendant'},
    {'title': 'The Red Door', 'lead': 'Nora', 'location': 'the boarded-up hospital',
     'warning': 'never open the red door', 'clue': 'a photograph with one face scratched out',
     'secret': 'A sealed patient ward holds evidence of a cover-up, and the anonymous warnings come from a witness.',
     'suspect': 'the former chief physician'},
]

def save(state):
    ROOT.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')

def load():
    if not STATE.exists():
        raise SystemExit('No story state yet. Run: python story_engine.py init --seed 4')
    return json.loads(STATE.read_text(encoding='utf-8'))

def scene(state, choice=None):
    num, length, m = state['episode'], state['length'], state['mystery']
    name = m['lead']
    prev = state['choices'][-1] if state['choices'] else None
    decision = {'YES': 'followed the suspicious lead', 'NO': 'held back and searched for another clue'}.get(prev, 'found an impossible clue')
    if num == 1:
        lines = [f'{name} received an anonymous recording: {m["warning"]}.',
                 f'The recording ended with a sound coming from {m["location"]}.',
                 f'Then {name} found {m["clue"]}.']
        question = f'Should {name} investigate tonight?'
    elif num == length:
        lines = [f'After {length - 1} nights, {name} finally understood the clues.',
                 f'The truth: {m["secret"]}',
                 f'{name} revealed the evidence. But someone else was still listening.']
        question = None
    elif num == length-1:
        lines = [f'{name} {decision}.',
                 f'The last clue pointed directly to {m["suspect"]}.',
                 'A hidden recording began playing—and someone knocked from the other side.']
        question = f'Should {name} confront them?'
    else:
        beats = [
            [f'{name} {decision}.', 'Footsteps stopped whenever the flashlight turned toward them.', f'A note appeared: "Ask {m["suspect"]} about the missing night."'],
            [f'{name} {decision}.', f'The walls of {m["location"]} concealed a narrow passage.', 'A second voice whispered: "The warning was not meant for you."'],
            [f'{name} {decision}.', f'The {m["clue"]} fitted a lock that was not there yesterday.', 'Behind it was a photograph taken tomorrow.'],
            [f'{name} {decision}.', 'A timestamp on the security footage changed while she watched.', f'The only person with a key was {m["suspect"]}.'],
        ]
        lines = beats[(num-2) % len(beats)]
        questions = [f'Should {name} follow the footsteps?', f'Should {name} open the passage?',
                     f'Should {name} use the key?', f'Should {name} question the caretaker?']
        question = questions[(num-2) % len(questions)]
    return {'title': m['title'], 'episode': num, 'total_episodes': length,
            'narration': lines, 'question': question,
            'on_screen': [line[:80] for line in lines],
            'caption': f'{m["title"]} | Episode {num}/{length}. '+
                       (f'{question} Comment YES or NO. #VoteTheMystery #MysterySeries' if question else 'The finale. #VoteTheMystery #MysterySeries'),
            'previous_vote': prev}

def init(seed):
    rng = random.Random(seed)
    mystery = rng.choice(MYSTERIES)
    state = {'episode': 1, 'length': rng.choice([8, 9, 10]), 'mystery': mystery, 'choices': [], 'seed': seed}
    save(state)
    output(scene(state))

def output(ep):
    ROOT.mkdir(exist_ok=True)
    (ROOT / 'current_episode.json').write_text(json.dumps(ep, indent=2) + '\n', encoding='utf-8')
    print(f'EPISODE {ep["episode"]}/{ep["total_episodes"]}: {ep["title"]}')
    for line in ep['narration']: print(' •', line)
    print('QUESTION:', ep['question'] or '(Finale: story ends)')

def next_episode(vote):
    state = load()
    if state['episode'] >= state['length']:
        raise SystemExit('Story complete. Start a new arc with init.')
    state['choices'].append(vote)
    state['episode'] += 1
    save(state)
    output(scene(state))

def demo(seed):
    init(seed)
    state=load()
    rng=random.Random(seed+100)
    while state['episode'] < state['length']:
        vote=rng.choice(['YES', 'NO'])
        print('\nSIMULATED WINNER:',vote)
        next_episode(vote)
        state=load()
    assert len(state['choices'])==state['length']-1
    print('\nVALIDATION PASSED: story ends after',state['length'],'episodes.')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['init','next','demo'])
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--vote',choices=['YES','NO'])
    args=parser.parse_args()
    if args.command=='init': init(args.seed)
    elif args.command=='demo': demo(args.seed)
    elif args.vote: next_episode(args.vote)
    else: parser.error('--vote YES or --vote NO required for next')
