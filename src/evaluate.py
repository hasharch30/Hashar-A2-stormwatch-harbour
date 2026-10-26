"""Paired evaluation and figures, with no new LLM calls unless --live is explicit."""
import csv
import itertools
import json
from pathlib import Path
import statistics as st
from .simulation import Harbour
from .master import Master

METRICS=['cargo_delivered','avg_ship_wait','crowding_violations','storm_knockouts']
POLICIES=['baseline','reflex','model','utility']

def write_csv(path,rows):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

def read_csv(path):
    with Path(path).open(encoding='utf-8') as f:
        return list(csv.DictReader(f))

def figures(rows,emergence,heats):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(9,5.4))
    labels=['Cargo delivered','Restricted mean queue wait (ticks)','Crowding cell-ticks','Storm knock-outs']
    for ax,m,label in zip(axes.flat,METRICS,labels):
        samples=[[r[m] for r in rows if r['agent']==p] for p in POLICIES]
        ax.bar(POLICIES,[st.mean(x) for x in samples],yerr=[st.stdev(x) for x in samples],
               color=['#bac4cf','#4d7f9b','#50776b','#d4974a'],capsize=4)
        ax.set_ylabel(label); ax.grid(axis='y',alpha=.16); ax.set_axisbelow(True)
    fig.suptitle('Figure 1  Thirty paired evaluation seeds (11-40); bars show mean +/- SD')
    fig.tight_layout(); fig.savefig('results/policy_comparison.png',dpi=180); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(9,3.4),sharey=True)
    vmax=max(max(max(row) for row in heat) for heat in heats.values())
    for ax,(name,heat) in zip(axes,heats.items()):
        im=ax.imshow(heat,cmap='magma',vmin=0,vmax=vmax,aspect='auto')
        ax.set_title(name+' routing, seed 11'); ax.set_xlabel('Column'); ax.set_ylabel('Row (north = 0)')
    fig.suptitle('Figure 2  Local route tie-breaking creates concentrated traffic')
    fig.subplots_adjust(top=.79,bottom=.17,wspace=.30,right=.84)
    cax=fig.add_axes([.88,.19,.018,.57])
    fig.colorbar(im,cax=cax,label='Worker cell-ticks')
    fig.savefig('results/emergence_heatmap.png',dpi=180); plt.close(fig)

def reproduce(live=False,digit=2):
    Path('results').mkdir(exist_ok=True)
    development=[]
    for p in POLICIES:
        for seed in range(1,11):
            development.append({'agent':p,'seed':seed,**Harbour(seed,p,digit).run()})
    write_csv('results/development.csv',development)
    rows=[]
    for p in POLICIES:
        for seed in range(11,41):
            rows.append({'agent':p,'seed':seed,**Harbour(seed,p,digit).run()})
    write_csv('results/evaluation_30_seeds.csv',rows)
    summary=[]
    for p in POLICIES:
        r={'agent':p}
        for m in METRICS:
            v=[x[m] for x in rows if x['agent']==p]
            r[m+'_mean']=st.mean(v); r[m+'_sd']=st.stdev(v)
        summary.append(r)
    write_csv('results/summary.csv',summary)
    pairs=[]
    for a,b in itertools.combinations(POLICIES,2):
        for m in METRICS:
            va=[x[m] for x in rows if x['agent']==a]; vb=[x[m] for x in rows if x['agent']==b]
            dif=[y-x for x,y in zip(va,vb)]; mean=st.mean(dif); sd=st.stdev(dif)
            se=sd/len(dif)**.5
            pairs.append({'from':a,'to':b,'metric':m,'paired_mean_difference':mean,'paired_sd':sd,
                          'ci95_low':mean-2.045*se,'ci95_high':mean+2.045*se,
                          'larger_than_paired_sd':abs(mean)>sd})
    write_csv('results/paired_comparisons.csv',pairs)
    emergence=[]; heats={}
    for routing in ['fixed','spread']:
        for seed in range(11,21):
            h=Harbour(seed,'utility',digit,routing=routing); result=h.run()
            # Exclude service cells: concentration should measure paths, not required stops.
            traffic=[h.heat[y][x] for y in range(1,14) for x in range(24)]
            total=sum(traffic)
            emergence.append({'routing':routing,'seed':seed,**result,
                              'top10_path_share':sum(sorted(traffic,reverse=True)[:10])/total})
            if seed==11:
                heats[routing]=h.heat
                write_csv(f'results/trace_{routing}_11.csv',
                          [{k:v for k,v in row.items() if k!='targets'} for row in h.trace])
    write_csv('results/emergence_10_seeds.csv',emergence)
    figures(rows,emergence,heats)
    # Safety-adjusted utility was chosen on development seeds only (20 cargo/knock-out).
    scores={p:st.mean(r['cargo_delivered']-20*r['storm_knockouts'] for r in development if r['agent']==p)
            for p in POLICIES[1:]}
    best=max(scores,key=scores.get)
    Path('results/selection.json').write_text(json.dumps({'development_scores':scores,'selected':best},indent=2))
    llmrows=[]
    log=Path('logs/llm_log.jsonl')
    if live and log.exists():
        raise ValueError('Archive logs/llm_log.jsonl before a fresh live experiment')
    if live or log.exists():
        for seed in range(11,16):
            control=Master(seed,replay=None if live else str(log))
            llmrows.append({'agent':'llm','seed':seed,**Harbour(seed,'llm',digit,control).run()})
            rule=next(r for r in rows if r['agent']==best and r['seed']==seed)
            llmrows.append({**rule,'invalid_outputs':0,'retries':0,'fallbacks':0,'calls':0,'time_per_call':0})
            print(json.dumps({'completed_llm_seed':seed,'metrics':llmrows[-2]}),flush=True)
        write_csv('results/llm_comparison.csv',llmrows)
        from .security import audit,run_security
        audit()
        security=Path('logs/security_log.jsonl')
        if security.exists() and len(security.read_text(encoding='utf-8').splitlines())==73:
            run_security(replay=True)
        if Path('results/hallucination_probes.csv').exists():
            from .report import generate
            generate()
    else:
        print('Rule experiments complete. Start local model and rerun --reproduce --live for LLM evidence.')
