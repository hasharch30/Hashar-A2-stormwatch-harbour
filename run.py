"""One-line JSON interface; python run.py --reproduce regenerates evaluation artifacts."""
import argparse
import json
from src.simulation import Harbour
from src.master import Master

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--agent',choices=['baseline','reflex','model','utility','llm'],default='utility')
    p.add_argument('--seed',type=int,default=11)
    p.add_argument('--digit',type=int,choices=range(10),default=2)
    p.add_argument('--replay',help='Path to original JSONL log; makes no model calls')
    p.add_argument('--routing',choices=['fixed','spread'],default='spread')
    p.add_argument('--human-approval',action='store_true',help='Prompt for EACH close/release order')
    p.add_argument('--reproduce',action='store_true')
    p.add_argument('--live',action='store_true',help='Use local server instead of replay in reproduction')
    args=p.parse_args()
    if args.reproduce:
        from src.evaluate import reproduce
        reproduce(live=args.live,digit=args.digit)
        return
    def approve(name,values,tick):
        import sys
        print(f'Approve {name}{values} at tick {tick}? Type APPROVE:',file=sys.stderr)
        return input().strip()=='APPROVE'
    master=Master(args.seed,replay=args.replay,approve=approve if args.human_approval else None) if args.agent=='llm' else None
    h=Harbour(args.seed,args.agent,args.digit,master,args.routing)
    print(json.dumps(h.run(),sort_keys=True))

if __name__=='__main__':
    main()
