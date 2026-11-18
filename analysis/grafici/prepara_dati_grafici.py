"""Export chapter-3 descriptive data; standard library only. Does not draw figures."""
import argparse,csv,hashlib,json,math,statistics
from collections import defaultdict
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-root',type=Path,required=True,help='Root of the consolidated TesiDiLaurea tree')
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'dati_grafici')
a=p.parse_args();root=a.data_root.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
sources={}
def remember(path):
 sources[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
 remember(path)
 with path.open(newline='') as f:return list(csv.DictReader(f))
def write(name,rows):
 assert rows
 with (out/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
expected={'L1':(61,450),'L2':(91,1440),'L3':(143,4259),'L4':(223,10383),'L5':(283,16148)}
per=[];total=0
for task in 'abc':
 for mode,prefix in [('local',610),('remote',710)]:
  for rep in range(1,6):
   run=prefix+rep;rows=read(root/f'task_{task}/results/{mode}/run_{run}.csv')
   if task=='b':
    assert len(rows)==48 and sum(r['phase']=='warmup' for r in rows)==3
    rows=[r for r in rows if r['phase']=='measured']
    assert len(rows)==45 and all(r['correct']=='True' for r in rows)
    assert all(int(r['seed'])==rep for r in rows)
   else:assert len(rows)==(100 if task=='a' else 500)
   assert all(int(r['run_id'])==run for r in rows)
   if task=='a':assert all(r['action']=='TURN_LEFT' for r in rows)
   total+=len(rows)
   groups=defaultdict(list)
   for r in rows:
    condition='all' if task=='a' else r['command_count'] if task=='b' else r['level']
    if task=='c':assert (int(r['path_length']),int(r['expanded_nodes']))==expected[condition]
    groups[condition].append(r)
   for condition,rr in sorted(groups.items()):
    assert len(rr)==({'a':100,'b':15,'c':100}[task])
    e2e=('e2e_time_ms' if mode=='local' else 'total_e2e_time_ms') if task=='a' else 'client_e2e_time_ms' if task=='b' else ('client_e2e_time_ms' if mode=='local' else 'total_e2e_time_ms')
    proc='processing_time_ms' if mode=='local' else 'remote_processing_time_ms'
    for metric,column in [('processing_ms',proc),('e2e_ms',e2e)]:
     vals=[float(r[column]) for r in rr];assert all(math.isfinite(x) and x>0 for x in vals)
     per.append(dict(task=task,mode=mode,condition=condition,replicate=rep,run_id=run,metric=metric,requests=len(rr),value=statistics.mean(vals)))
assert total==6450
write('tempi_per_replica.csv',per)
summ=[]
for task,mode,condition,metric in sorted({(r['task'],r['mode'],r['condition'],r['metric']) for r in per}):
 vals=[r['value'] for r in per if (r['task'],r['mode'],r['condition'],r['metric'])==(task,mode,condition,metric)]
 assert len(vals)==5
 summ.append(dict(task=task,mode=mode,condition=condition,metric=metric,replicates=5,mean=statistics.mean(vals),sd=statistics.stdev(vals),unit='ms'))
write('tempi_sintesi.csv',summ)
ratios=[]
for task,condition in sorted({(r['task'],r['condition']) for r in summ}):
 vals={r['mode']:r['mean'] for r in summ if r['task']==task and r['condition']==condition and r['metric']=='e2e_ms'}
 ratios.append(dict(task=task,condition=condition,speedup_ratio_of_means=vals['local']/vals['remote'],remote_reduction_percent=100*(1-vals['remote']/vals['local'])))
write('speedup_descrittivo.csv',ratios)
for filename in ['resources_per_run.csv','resources_summary.csv']:
 rows=read(root/'analysis'/filename)
 assert len(rows)==(70 if filename=='resources_per_run.csv' else 14)
 write(filename,rows)
functional=[];traces=[];paths=[]
for task in ['b','c']:
 for mode in ['local','remote']:
  folder=root/f'task_{task}/functional_checks'
  pattern=f'task_b_sequence_{mode}_*.json' if task=='b' else f'task_c_L1_{mode}_*.json'
  files=list(folder.glob(pattern));assert len(files)==1
  fp=files[0];remember(fp);d=json.loads(fp.read_text());assert d['functional_pass']
  functional.append(dict(task=task,mode=mode,http_s=d['http_e2e_wall_s'],execution_s=d['execution_until_stop_confirmed_wall_s'],total_s=d['total_request_to_completion_wall_s'],goal_error_m=d.get('goal_error_m',''),observations=1,source=fp.name))
  if task=='c':
   for i,t in enumerate(d['trace']):traces.append(dict(mode=mode,index=i,x_m=t['x'],y_m=t['y'],sim_seconds=t['sim_seconds']))
   mp=root/'task_c/ubuntu/task_c/maps/L1.json';remember(mp);m=json.loads(mp.read_text())
   if mode=='local':
    (out/'L1_mappa.json').write_text(json.dumps(m))
    for i,(r,c) in enumerate(d['recognition']['path']):paths.append(dict(index=i,row=r,col=c,x_m=m['origin'][0]+(c+.5)*m['resolution'],y_m=m['origin'][1]+(r+.5)*m['resolution']))
write('movimento_sintesi.csv',functional);write('C_L1_tracce.csv',traces);write('C_L1_percorso.csv',paths)
(out/'provenienza.json').write_text(json.dumps(dict(temporal_measured_requests=total,temporal_replica_metric_rows=len(per),resource_blocks=70,source_sha256=sources),indent=2)+'\n')
print('Validated 6450 temporal observations; exported descriptive tables, resource tables, functional summaries and L1 geometry.')
for r in summ:
 print(r['task'],r['mode'],r['condition'],r['metric'],f"{r['mean']:.6f}",f"SD={r['sd']:.6f}")
