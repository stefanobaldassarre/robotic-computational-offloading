import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import selectors
import subprocess
import time
import requests

p = argparse.ArgumentParser()
p.add_argument('mode', choices=['local', 'remote'])
p.add_argument('--maps', type=Path, default=Path.home()/'tesi_gazebo/task_c/maps')
a = p.parse_args()
expected = {'L1': (61,450), 'L2': (91,1440), 'L3': (143,4259),
            'L4': (223,10383), 'L5': (283,16148)}
prepared = []
for level in expected:
    raw = (a.maps/f'{level}.json').read_bytes()
    d = json.loads(raw)
    payload = {'level':level, 'grid':d['grid'], 'start':d['start'], 'goal':d['goal']}
    prepared.append((level, payload, hashlib.sha256(raw).hexdigest()))
url = 'http://192.168.50.20:'+('5200' if a.mode=='local' else '5202')+'/process'
container = 'task-c-local' if a.mode=='local' else 'task-c-proxy'
base = Path.home()/'tesi_gazebo/results/resource_pilot_c'
base.mkdir(parents=True, exist_ok=True)

def request(payload):
    start = time.perf_counter()
    response = requests.post(url, json=payload, timeout=(5,30))
    elapsed = (time.perf_counter()-start)*1000
    response.raise_for_status()
    result = response.json()
    level = payload['level']
    if (result['path_length'], result['expanded_nodes']) != expected[level]:
        raise RuntimeError('Risultato A* inatteso: '+level)
    return result, elapsed

for level, payload, digest in prepared:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f')
    label = f'c_{a.mode}_{level}_resource_pilot_{stamp}'
    out = base/label
    print(f'Livello {level}: 3 warm-up', flush=True)
    for _ in range(3):
        request(payload)
    ssh = ['ssh', '-i', str(Path.home()/'.ssh/tesi_monitor_ed25519'),
           '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
           '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=3',
           'raspberry@192.168.50.20',
           f'python3 -u ~/tesi/resource_monitor/agent.py {container} {label}']
    meta = dict(mode=a.mode, level=level, label=label, status='running',
                map_sha256=digest, warmup_count=3, measured_count=100,
                windows=[], protocol='pilot_C_ascending_levels_100_requests')
    with out.with_suffix('.ssh.log').open('x') as log:
        proc = subprocess.Popen(ssh, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=log, text=True, bufsize=1)
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        def receive(expected_event):
            if not selector.select(30):
                raise RuntimeError('Timeout risposta monitor')
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError('Monitor terminato: consultare ssh.log')
            message = json.loads(line)
            if message['event'] != expected_event:
                raise RuntimeError('Evento monitor inatteso: '+line)
            return message
        def control(event, **kw):
            proc.stdin.write(json.dumps(dict(event=event, **kw))+'\n')
            proc.stdin.flush()
        try:
            meta['agent'] = receive('READY')
            control('BEGIN', phase='idle')
            receive('BEGUN')
            time.sleep(10)
            control('END')
            meta['windows'].append(receive('ENDED'))
            with out.with_suffix('.csv').open('x', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['sample_id','level','map_sha256',
                                                       'http_e2e_ms','result_json'])
                writer.writeheader()
                control('BEGIN', phase='active')
                receive('BEGUN')
                for sample_id in range(1,101):
                    result, elapsed = request(payload)
                    writer.writerow(dict(sample_id=sample_id, level=level,
                                         map_sha256=digest, http_e2e_ms=elapsed,
                                         result_json=json.dumps(result)))
                    f.flush()
                    if sample_id % 20 == 0:
                        print(f'{level}: {sample_id}/100 validi', flush=True)
                control('END')
                meta['windows'].append(receive('ENDED'))
            control('QUIT')
            receive('DONE')
            proc.stdin.close()
            if proc.wait(timeout=10) != 0:
                raise RuntimeError('Errore processo monitor')
            meta['status'] = 'completed'
        finally:
            if proc.poll() is None:
                proc.stdin.close()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    proc.wait(timeout=5)
            selector.close()
            with out.with_suffix('.json').open('x') as f:
                json.dump(meta, f, indent=2)
    print(json.dumps(meta, indent=2), flush=True)
print('PILOT C COMPLETATO: 5 livelli, 500 richieste valide', flush=True)
