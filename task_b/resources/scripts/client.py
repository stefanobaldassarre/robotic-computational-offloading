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

p=argparse.ArgumentParser()
p.add_argument('mode', choices=['local','remote'])
p.add_argument('--dataset', type=Path, required=True)
a=p.parse_args()
items=json.loads((a.dataset/'manifest.json').read_text())
if len(items)!=15 or len({x['file'] for x in items})!=15:
    raise ValueError('Expected 15 distinct inputs')
prepared=[]
for item in items:
    raw=(a.dataset/'wav'/item['file']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=item['sha256']:
        raise ValueError('Checksum mismatch')
    prepared.append((item,raw))
url='http://192.168.50.20:'+('5300' if a.mode=='local' else '5302')+'/process'
container='task-b-audio-local' if a.mode=='local' else 'task-b-audio-proxy'
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f')
label=f'b_{a.mode}_resource_pilot_{stamp}'
out=Path.home()/'tesi_gazebo/results/resource_pilot'/label
out.parent.mkdir(parents=True,exist_ok=True)

# Warm-ups happen before resource windows, with service model already loaded.
for name in ['S1_01.wav','S3_01.wav','S5_01.wav']:
    item,raw=next((i,r) for i,r in prepared if i['file']==name)
    response=requests.post(url,data=raw,headers={'Content-Type':'audio/wav'},timeout=(5,60))
    response.raise_for_status()
    if response.json()['commands']!=item['expected_commands']:
        raise RuntimeError('Warm-up recognition mismatch')
    print('Warm-up:',name,flush=True)

ssh=['ssh','-i',str(Path.home()/'.ssh/tesi_monitor_ed25519'),
     '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=5',
     '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=3',
     'raspberry@192.168.50.20',
     f'python3 -u ~/tesi/resource_monitor/agent.py {container} {label}']
meta=dict(mode=a.mode,label=label,status='running',windows=[])
with out.with_suffix('.ssh.log').open('x') as log:
    proc=subprocess.Popen(ssh,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,
                          text=True,bufsize=1)
    selector=selectors.DefaultSelector()
    selector.register(proc.stdout,selectors.EVENT_READ)
    def receive(expected):
        if not selector.select(30):
            raise RuntimeError('Monitor acknowledgement timeout')
        line=proc.stdout.readline()
        if not line:
            raise RuntimeError('Monitor ended: inspect SSH log')
        message=json.loads(line)
        if message['event']!=expected:
            raise RuntimeError('Unexpected monitor event: '+line)
        return message
    def control(event, **kw):
        proc.stdin.write(json.dumps(dict(event=event,**kw))+'\n')
        proc.stdin.flush()
    try:
        meta['agent']=receive('READY')
        control('BEGIN',phase='idle')
        receive('BEGUN')
        time.sleep(10)
        control('END')
        meta['windows'].append(receive('ENDED'))
        print('Riposo registrato; inizio 15 richieste',flush=True)
        with out.with_suffix('.csv').open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['sample_id','file','command_count','sha256','correct','http_e2e_ms','result_json'])
            writer.writeheader()
            control('BEGIN',phase='active')
            receive('BEGUN')
            for n,(item,raw) in enumerate(prepared,1):
                start=time.perf_counter()
                response=requests.post(url,data=raw,headers={'Content-Type':'audio/wav'},timeout=(5,60))
                elapsed=(time.perf_counter()-start)*1000
                response.raise_for_status()
                result=response.json()
                ok=result['commands']==item['expected_commands']
                writer.writerow(dict(sample_id=n,file=item['file'],command_count=item['command_count'],
                                     sha256=item['sha256'],correct=ok,http_e2e_ms=elapsed,
                                     result_json=json.dumps(result)))
                f.flush()
                print(f'{n}/15 {item["file"]} correct={ok}',flush=True)
            control('END')
            meta['windows'].append(receive('ENDED'))
        control('QUIT')
        receive('DONE')
        proc.stdin.close()
        if proc.wait(timeout=10)!=0:
            raise RuntimeError('Monitor failed')
        meta['status']='completed'
    finally:
        if proc.poll() is None:
            proc.stdin.close()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=5)
        with out.with_suffix('.json').open('x') as f:json.dump(meta,f,indent=2)
print(json.dumps(meta,indent=2))
print('File Ubuntu:',out)
