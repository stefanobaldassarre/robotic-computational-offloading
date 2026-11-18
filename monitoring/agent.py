import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('container')
p.add_argument('label')
a = p.parse_args()
if not a.label.replace('_', '').replace('-', '').isalnum():
    raise ValueError('Invalid label')
info = json.loads(subprocess.check_output(['docker', 'inspect', a.container], text=True))[0]
pid = info['State']['Pid']
if not info['State']['Running'] or pid <= 0:
    raise RuntimeError('Container not running')
rel = next(x.split(':', 2)[2] for x in Path(f'/proc/{pid}/cgroup').read_text().splitlines() if x.startswith('0::'))
root = Path('/sys/fs/cgroup').resolve()
group = (root / rel.lstrip('/')).resolve()
if not group.is_relative_to(root):
    raise RuntimeError('Invalid cgroup path')
inode = group.stat().st_ino

def pairs(name):
    return {k: int(v) for k, v in (line.split() for line in (group/name).read_text().splitlines())}

def sample():
    if group.stat().st_ino != inode:
        raise RuntimeError('Container cgroup changed')
    cpu = pairs('cpu.stat')
    mem = pairs('memory.stat')
    return dict(wall=time.perf_counter(), cpu_usage_usec=cpu['usage_usec'],
                memory_current_bytes=int((group/'memory.current').read_text()),
                memory_anon_bytes=mem['anon'], memory_file_bytes=mem['file'],
                memory_kernel_bytes=mem.get('kernel', 0),
                memory_inactive_file_bytes=mem['inactive_file'],
                memory_swap_bytes=int((group/'memory.swap.current').read_text()))

def emit(obj):
    print(json.dumps(obj), flush=True)

stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f')
base = Path.home()/'tesi/resource_monitor/results'/f'{a.label}_{stamp}'
base.parent.mkdir(parents=True, exist_ok=True)
meta = dict(container=a.container, container_id=info['Id'], image_id=info['Image'],
            label=a.label, kernel=os.uname().release,
            kernel_cmdline=Path('/proc/cmdline').read_text().strip(),
            cpus=os.cpu_count(), cpu_max=(group/'cpu.max').read_text().strip(),
            effective_cpus=(group/'cpuset.cpus.effective').read_text().strip(),
            memory_events_before=pairs('memory.events'), windows=[], status='running')
initial = sample()
phase = 'waiting'
previous = initial
opened = None
fields = ['phase', 'event', 'elapsed_s', 'cpu_percent_one_core', 'cpu_percent_host'] + list(initial)
fields.remove('wall')
try:
    with base.with_suffix('.csv').open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        def record(event):
            global previous
            current = sample()
            dt = current['wall'] - previous['wall']
            delta = current['cpu_usage_usec']-previous['cpu_usage_usec']
            if delta < 0:
                raise RuntimeError('CPU counter reset')
            percent = 100*delta/(dt*1e6) if dt > 0 else 0
            row = {k:v for k,v in current.items() if k!='wall'}
            row.update(phase=phase, event=event, elapsed_s=current['wall']-initial['wall'],
                       cpu_percent_one_core=percent, cpu_percent_host=percent/meta['cpus'])
            writer.writerow(row)
            f.flush()
            previous = current
            return current
        emit(dict(event='READY', base=str(base)))
        deadline = time.perf_counter()+600
        next_tick = time.perf_counter()+0.2
        while True:
            now = time.perf_counter()
            if now > deadline:
                raise RuntimeError('Agent safety timeout')
            ready, _, _ = select.select([sys.stdin], [], [], max(0, min(next_tick-now, 0.2)))
            if ready:
                line = sys.stdin.readline()
                if not line:
                    raise RuntimeError('SSH control channel closed')
                cmd = json.loads(line)
                event = cmd['event']
                if event == 'BEGIN':
                    if opened is not None or cmd['phase'] not in ['idle', 'active']:
                        raise RuntimeError('Invalid phase transition')
                    record('pre_begin')
                    phase = cmd['phase']
                    opened = record('begin')
                    emit(dict(event='BEGUN', phase=phase))
                elif event == 'END':
                    if opened is None:
                        raise RuntimeError('No open phase')
                    end = record('end')
                    window = dict(phase=phase, elapsed_s=end['wall']-opened['wall'],
                                  cpu_seconds=(end['cpu_usage_usec']-opened['cpu_usage_usec'])/1e6,
                                  memory_start_bytes=opened['memory_current_bytes'],
                                  memory_end_bytes=end['memory_current_bytes'])
                    meta['windows'].append(window)
                    opened = None
                    phase = 'waiting'
                    emit(dict(event='ENDED', **window))
                elif event == 'QUIT':
                    if opened is not None:
                        raise RuntimeError('Unclosed phase')
                    meta['status'] = 'completed'
                    emit(dict(event='DONE', base=str(base)))
                    break
                else:
                    raise RuntimeError('Unknown control event')
            if time.perf_counter() >= next_tick:
                record('sample')
                next_tick = time.perf_counter()+0.2
finally:
    meta['memory_events_after'] = pairs('memory.events')
    with base.with_suffix('.json').open('x') as f:
        json.dump(meta, f, indent=2)
