import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import time
import requests

p = argparse.ArgumentParser()
p.add_argument('mode', choices=['local', 'remote'])
p.add_argument('run_id', type=int)
p.add_argument('--dataset', type=Path, required=True)
p.add_argument('--seed', type=int, required=True, choices=range(1, 6))
a = p.parse_args()
items = json.loads((a.dataset / 'manifest.json').read_text())
if len(items) != 15 or len({x['file'] for x in items}) != 15:
    raise ValueError('Expected 15 distinct files')
prepared = []
for item in items:
    raw = (a.dataset / 'wav' / item['file']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise ValueError('Checksum mismatch: ' + item['file'])
    prepared.append((item, raw))
for count in (1, 3, 5):
    if sum(i['command_count'] == count for i, _ in prepared) != 5:
        raise ValueError('Expected five inputs per length')
rng = random.Random(a.seed)
plan = []
for repeat in range(1, 4):
    order = prepared.copy()
    rng.shuffle(order)
    plan.extend((repeat, item, raw) for item, raw in order)
warmups = [next((i, raw) for i, raw in prepared if i['file'] == name)
           for name in ('S1_01.wav', 'S3_01.wav', 'S5_01.wav')]
url = 'http://192.168.50.20:' + ('5300' if a.mode == 'local' else '5302') + '/process'
out = Path.home() / 'tesi_gazebo/results/task_b_audio_lan' / a.mode / f'run_{a.run_id}.csv'
out.parent.mkdir(parents=True, exist_ok=True)
fields = ['timestamp', 'mode', 'run_id', 'seed', 'phase', 'sample_id', 'repeat_id', 'file',
          'command_count', 'expected', 'text', 'commands', 'correct', 'audio_seconds',
          'payload_bytes', 'sha256', 'processing_time_ms', 'service_time_ms',
          'remote_processing_time_ms', 'remote_service_time_ms', 'offload_e2e_time_ms',
          'proxy_service_time_ms', 'client_e2e_time_ms']

def send(item, raw):
    start = time.perf_counter()
    response = requests.post(url, data=raw, headers={'Content-Type': 'audio/wav'}, timeout=(5, 60))
    elapsed = (time.perf_counter() - start) * 1000
    response.raise_for_status()
    result = response.json()
    keys = (['processing_time_ms', 'service_time_ms'] if a.mode == 'local' else
            ['remote_processing_time_ms', 'remote_service_time_ms', 'offload_e2e_time_ms', 'proxy_service_time_ms'])
    for key in keys:
        value = float(result[key])
        if not math.isfinite(value) or value < 0:
            raise ValueError('Invalid timing: ' + key)
    if result['payload_bytes'] != len(raw) or abs(result['audio_seconds'] - item['duration_seconds']) > 1e-6:
        raise ValueError('Payload metadata mismatch')
    if not isinstance(result['commands'], list) or not isinstance(result['text'], str):
        raise ValueError('Invalid recognition response')
    return result, elapsed

# Reserve exclusive file before requests; incomplete outputs retained for diagnosis.
with out.open('x', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    f.flush()
    correct = 0
    for phase, requests_plan in [('warmup', [(0, i, raw) for i, raw in warmups]), ('measured', plan)]:
        for sample, (repeat, item, raw) in enumerate(requests_plan, 1):
            result, elapsed = send(item, raw)
            ok = result['commands'] == item['expected_commands']
            if phase == 'measured':
                correct += int(ok)
            row = {k: result[k] for k in fields if k in result}
            row.update(timestamp=datetime.now(timezone.utc).isoformat(), mode=a.mode,
                       run_id=a.run_id, seed=a.seed, phase=phase, sample_id=sample, repeat_id=repeat,
                       file=item['file'], command_count=item['command_count'],
                       expected=json.dumps(item['expected_commands']), commands=json.dumps(result['commands']),
                       correct=ok, sha256=item['sha256'], client_e2e_time_ms=elapsed)
            writer.writerow(row)
            f.flush()
            print(f'{phase} {sample}/{len(requests_plan)} {item["file"]} correct={ok} E2E={elapsed:.1f} ms', flush=True)
    print(f'COMPLETE: 3 warm-up + 45 measured; correct={correct}/45; CSV={out}')
