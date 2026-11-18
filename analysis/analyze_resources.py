"""Validate selected raw resource campaigns and rebuild derived tables (stdlib only)."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).parent
EXPECTED = {'L1':(61,450),'L2':(91,1440),'L3':(143,4259),'L4':(223,10383),'L5':(283,16148)}
records=[]
issues=[]
for task in 'abc':
    resource=ROOT/f'task_{task}/resources'
    index=json.loads((resource/'runs.json').read_text())
    assert len(index)==(50 if task=='c' else 10)
    for entry in index:
        def load_json(key):return json.loads((ROOT/entry[key]).read_text())
        def load_csv(key):
            with (ROOT/entry[key]).open(newline='') as f:return list(csv.DictReader(f))
        client=load_json('ubuntu_json');agent=load_json('raspberry_json')
        assert client['status']==agent['status']=='completed'
        assert client['label']==agent['label']==entry['label']
        assert agent['memory_events_before']==agent['memory_events_after']
        replies=load_csv('ubuntu_csv')
        count={'a':300,'b':15,'c':100}[task]
        assert len(replies)==count
        assert [int(r['sample_id']) for r in replies]==list(range(1,count+1))
        for r in replies:
            q=json.loads(r['result_json'])
            assert math.isfinite(float(r.get('http_e2e_ms',0)))
            if task=='a':
                manifest=client['image_manifest']
                raw=(resource/'dataset'/manifest['file']).read_bytes()
                assert hashlib.sha256(raw).hexdigest()==manifest['sha256']==r['image_sha256']
                assert q['action']=='TURN_LEFT' and abs(q['red_ratio']-.5868055555555556)<1e-6
            elif task=='b':
                manifest=json.loads((ROOT/'task_b/dataset/manifest.json').read_text())
                item=next(x for x in manifest if x['file']==r['file'])
                raw=(ROOT/'task_b/dataset/wav'/r['file']).read_bytes()
                assert hashlib.sha256(raw).hexdigest()==item['sha256']==r['sha256']
                assert q['commands']==item['expected_commands'] and r['correct']=='True'
            else:
                assert (q['path_length'],q['expanded_nodes'])==EXPECTED[entry['level']]
                map_path=ROOT/'task_c/ubuntu/task_c/maps'/f"{entry['level']}.json"
                assert hashlib.sha256(map_path.read_bytes()).hexdigest()==client['map_sha256']==r['map_sha256']
        samples=load_csv('raspberry_csv')
        active=[r for r in samples if r['phase']=='active']
        assert active[0]['event']=='begin' and active[-1]['event']=='end'
        intervals=[float(b['elapsed_s'])-float(a['elapsed_s']) for a,b in zip(active,active[1:])]
        assert min(intervals)>0
        duration=sum(intervals)
        cpu=(int(active[-1]['cpu_usage_usec'])-int(active[0]['cpu_usage_usec']))/1e6
        window=next(w for w in client['windows'] if w['phase']=='active')
        assert abs(cpu-window['cpu_seconds'])<1e-8 and abs(duration-window['elapsed_s'])<1e-8
        assert all(int(r['memory_swap_bytes'])==0 for r in samples)
        def weighted(key):
            return sum((float(a[key])+float(b[key]))/2*dt
                       for a,b,dt in zip(active,active[1:],intervals))/duration/1048576
        regular=[float(b['elapsed_s'])-float(a['elapsed_s']) for a,b in zip(active,active[1:])
                 if a['event']==b['event']=='sample']
        maxgap=max(regular,default=0)
        if maxgap>.4:issues.append(dict(label=entry['label'],max_sample_gap_s=maxgap))
        records.append(dict(task=task,mode=entry['mode'],level=entry['level'],replicate=entry['replicate'],
                            label=entry['label'],requests=count,duration_s=duration,cpu_seconds=cpu,
                            cpu_seconds_per_request=cpu/count,cpu_percent_one_core=100*cpu/duration,
                            cpu_percent_host=100*cpu/duration/agent['cpus'],
                            memory_mean_mib=weighted('memory_current_bytes'),
                            memory_anon_mean_mib=weighted('memory_anon_bytes'),
                            memory_file_mean_mib=weighted('memory_file_bytes'),
                            memory_sampled_max_mib=max(int(r['memory_current_bytes']) for r in active)/1048576,
                            max_sample_gap_s=maxgap))
records.sort(key=lambda x:(x['task'],x['level'],x['mode'],x['replicate']))
with (OUT/'resources_per_run.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
summary=[]
for task,mode,level in sorted({(r['task'],r['mode'],r['level']) for r in records}):
    subset=[r for r in records if (r['task'],r['mode'],r['level'])==(task,mode,level)]
    assert len(subset)==5
    row=dict(task=task,mode=mode,level=level,replicates=5)
    for key in list(records[0])[6:]:
        if key=='requests':continue
        values=[r[key] for r in subset]
        row[key+'_mean']=statistics.mean(values)
        row[key+'_sd']=statistics.stdev(values)
    summary.append(row)
with (OUT/'resources_summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
(OUT/'resource_quality.json').write_text(json.dumps(dict(
    selected_blocks=len(records),measured_requests=sum(r['requests'] for r in records),
    selection='Explicit runs.json files; pilots and extra attempts excluded',
    long_sample_gaps=issues,validation='passed'),indent=2)+'\n')
print(f'Validated {len(records)} blocks, {sum(r["requests"] for r in records)} measured requests.')
print('Derived tables rebuilt; long sample gaps:',len(issues))
