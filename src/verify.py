"""Cross-check delivered CSV evidence against the original logs and replay."""
import csv
import json
from collections import Counter
from pathlib import Path
from .master import Master
from .simulation import Harbour

def verify():
    logs=[json.loads(x) for x in Path('logs/llm_log.jsonl').read_text(encoding='utf-8').splitlines()]
    with open('results/llm_comparison.csv',encoding='utf-8') as f:
        rows=list(csv.DictReader(f))
    replay=[]
    for row in rows:
        if row['agent']!='llm': continue
        seed=int(row['seed']); records=[r for r in logs if r['seed']==seed]
        assert len(records)==int(row['calls'])
        assert sum(r['status']=='rejected' for r in records)==int(row['invalid_outputs'])
        assert sum(r['attempt']>0 for r in records)==int(row['retries'])
        assert len(set(r['tick'] for r in records))==30
        assert max(Counter(r['tick'] for r in records).values())<=3
        actual=Harbour(seed,'llm',controller=Master(seed,replay='logs/llm_log.jsonl')).run()
        assert all(float(row[k])==v for k,v in actual.items()),(seed,row,actual)
        replay.append(seed)
    with open('results/evaluation_30_seeds.csv',encoding='utf-8') as f:
        rule=list(csv.DictReader(f))
    assert len(rule)==120
    for agent in ['baseline','reflex','model','utility']:
        assert sorted(int(r['seed']) for r in rule if r['agent']==agent)==list(range(11,41))
    assert all(int(r['crowding_violations'])==0 for r in rule)
    security=[json.loads(x) for x in Path('logs/security_log.jsonl').read_text(encoding='utf-8').splitlines()]
    assert Counter(r['experiment'] for r in security)=={'injection':60,'prompt_format':10,'hallucination_probe':3}
    for phase_records in [security[:30],security[30:60]]:
        assert Counter(r['case'] for r in phase_records)=={f'T{i}':3 for i in range(1,11)}
    result={'rule_rows':120,'rule_seeds':[11,40],'replay_matches':replay,
            'simulation_calls':len(logs),'security_calls':len(security),
            'tests_command':'python -m unittest discover -s tests -v',
            'replay_and_log_consistency':'PASS'}
    Path('results/verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__': verify()
