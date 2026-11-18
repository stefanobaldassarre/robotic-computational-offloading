import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import selectors
import subprocess
import time
import requests

p = argparse.ArgumentParser()
p.add_argument('mode', choices=['local','remote'])
p.add_argument('--dataset', type=Path, default=Path.home()/'tesi_gazebo/task_a_resources/dataset')
a = p.parse_args()
manifest = json.loads((a.dataset/'manifest.json').read_text())
raw = (a.dataset/manifest['file']).read_bytes()
if hashlib.sha256(raw).hexdigest() != manifest['sha256'] or len(raw) != manifest['payload_bytes']:
    raise ValueError('JPEG non corrispondente al manifest')
url = 'http://192.168.50.20:'+('5000' if a.mode=='local' else '5002')+'/process'
container = 'task-a-local' if a.mode=='local' else 'task-a-proxy'

def request():
    start = time.perf_counter()
    response = requests.post(url, files={'image':('frame.jpg',raw,'image/jpeg')}, timeout=(5,10))
    elapsed = (time.perf_counter()-start)*1000
    response.raise_for_status()
    result = response.json()
    if result.get('action') != 'TURN_LEFT':
        raise RuntimeError('Azione diversa da quella attesa per il frame pilota')
    ratio = float(result['red_ratio'])
    if not math.isfinite(ratio) or abs(ratio-0.5868055555555556)>1e-6:
        raise RuntimeError('red_ratio diverso dal frame verificato')
    keys = ['processing_time_ms','service_time_ms'] if a.mode=='local' else ['remote_processing_time_ms','remote_service_time_ms','offload_e2e_time_ms']
    for key in keys:
        value = float(result[key])
        if not math.isfinite(value) or value<0:
            raise RuntimeError('Tempo non valido: '+key)
    return result, elapsed

for i in range(10):
    request()
print('10 warm-up completati',flush=True)
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f')
label = f'a_{a.mode}_resource_pilot_{stamp}'
out = Path.home()/'tesi_gazebo/results/resource_pilot_a'/label
out.parent.mkdir(parents=True,exist_ok=True)
meta = dict(mode=a.mode,label=label,status='running',image_manifest=manifest,
            warmup_count=10,measured_count=300,windows=[],
            protocol='fixed_JPEG_300_serial_requests_no_pacing')
ssh = ['ssh','-i',str(Path.home()/'.ssh/tesi_monitor_ed25519'),
       '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=5',
       '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=3',
       'raspberry@192.168.50.20',
       f'python3 -u ~/tesi/resource_monitor/agent.py {container} {label}']
with out.with_suffix('.ssh.log').open('x') as log:
    proc = subprocess.Popen(ssh,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                            stderr=log,text=True,bufsize=1)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout,selectors.EVENT_READ)
    def receive(expected):
        if not selector.select(30):
            raise RuntimeError('Timeout monitor')
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError('Monitor terminato: consultare ssh.log')
        message = json.loads(line)
        if message['event'] != expected:
            raise RuntimeError('Evento monitor inatteso: '+line)
        return message
    def control(event,**kw):
        proc.stdin.write(json.dumps(dict(event=event,**kw))+'\n')
        proc.stdin.flush()
    try:
        meta['agent'] = receive('READY')
        control('BEGIN',phase='idle')
        receive('BEGUN')
        time.sleep(10)
        control('END')
        meta['windows'].append(receive('ENDED'))
        print('Riposo registrato; inizio 300 richieste',flush=True)
        with out.with_suffix('.csv').open('x',newline='') as f:
            writer = csv.DictWriter(f,fieldnames=['sample_id','image_sha256','http_e2e_ms','result_json'])
            writer.writeheader()
            control('BEGIN',phase='active')
            receive('BEGUN')
            for sample_id in range(1,301):
                result,elapsed = request()
                writer.writerow(dict(sample_id=sample_id,image_sha256=manifest['sha256'],
                                     http_e2e_ms=elapsed,result_json=json.dumps(result)))
                f.flush()
                if sample_id%50==0:
                    print(f'{sample_id}/300 validi',flush=True)
            control('END')
            meta['windows'].append(receive('ENDED'))
        control('QUIT')
        receive('DONE')
        proc.stdin.close()
        if proc.wait(timeout=10)!=0:
            raise RuntimeError('Errore monitor')
        meta['status']='completed'
    finally:
        if proc.poll() is None:
            proc.stdin.close()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=5)
        selector.close()
        with out.with_suffix('.json').open('x') as f:json.dump(meta,f,indent=2)
print(json.dumps(meta,indent=2))
print('PILOT A COMPLETATO: 300 richieste valide')
print('File Ubuntu:',out)
