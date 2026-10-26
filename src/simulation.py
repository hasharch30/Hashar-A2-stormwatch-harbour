"""Discrete harbour. All environmental randomness is scheduled by one Random(seed)."""
from collections import Counter, deque
from dataclasses import dataclass
import random

PARAMETERS = [(10,6,10,3,8),(12,5,9,4,8),(14,6,10,4,9),
              (16,5,9,5,9),(10,5,9,5,10),(12,6,10,3,10),
              (14,5,9,3,7),(16,6,10,4,7),(12,4,8,5,8),(14,4,8,4,9)]
BERTHS = {'B1':(3,0),'B2':(9,0),'B3':(15,0),'B4':(21,0)}
WAREHOUSE = (0,15)
TICKS = 600

def distance(a,b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])

@dataclass
class Ship:
    id: int
    arrived: int
    cargo: int
    berth: str = None
    docked: int = None
    departed: int = None
    held_until: int = -1

@dataclass
class Worker:
    id: int
    pos: tuple
    carrying: bool = False
    knocked_until: int = -1
    target: str = None
    remembers_until: int = -1

class Harbour:
    def __init__(self, seed, policy, digit=2, controller=None, routing='spread'):
        self.seed, self.policy, self.digit = seed, policy, digit
        self.nworkers, lo, hi, nstorms, self.units = PARAMETERS[digit]
        rng = random.Random(seed)
        # Generate exogenous events BEFORE agents act, enabling paired comparisons.
        self.arrivals = []
        t = rng.randint(lo,hi)
        while t < TICKS:
            self.arrivals.append(t)
            t += rng.randint(lo,hi)
        # One storm in each equal time window; at least 25 ticks between storms.
        width = 540 // nstorms
        self.storms = [rng.randint(25+i*width,25+(i+1)*width-30) for i in range(nstorms)]
        self.workers = [Worker(i,(i%5,14+i//5%2)) for i in range(self.nworkers)]
        self.ships = []
        self.berths = {b:None for b in BERTHS}
        self.tick = 0
        self.delivered = self.lost = self.knockouts = self.violations = 0
        self.heat = [[0]*24 for _ in range(16)]
        self.trace = []
        self.controller = controller
        self.routing = routing
        self.closed = False
        self.orders = {}
        self.feedback = ['No previous orders.']
        self.bulletin = {b:0 for b in BERTHS}

    def storm_active(self):
        return any(s <= self.tick < s+15 for s in self.storms)

    def warning(self):
        return any(self.tick == s-5 for s in self.storms)

    def ship(self, sid):
        return next((s for s in self.ships if s.id == sid), None)

    def is_risk(self,w):
        if self.policy == 'reflex':
            return self.warning()
        return self.tick < w.remembers_until

    def choose_target(self,w):
        known = self.bulletin.copy()
        for b,p in BERTHS.items():
            if distance(w.pos,p)<=4:
                s = self.ship(self.berths[b])
                known[b] = s.cargo if s else 0
        available = [b for b in BERTHS if known[b]>0 and not
                     (b in ('B1','B4') and self.is_risk(w))]
        if self.policy == 'reflex':
            # Stateless choice: current broadcast + current visible berth snapshot.
            available = [b for b in BERTHS if self.berths[b] is not None and not
                         (b in ('B1','B4') and self.warning())]
            return min(available,key=lambda b:(distance(w.pos,BERTHS[b]),b)) if available else None
        if self.policy == 'model':
            if w.target in available:
                return w.target
            return min(available,key=lambda b:(distance(w.pos,BERTHS[b]),b)) if available else None
        # Utility has five factors; counts depend only on the current state.
        if self.policy == 'llm' and w.id in self.orders:
            b = self.orders[w.id]
            if b in available:
                return b
        def score(b):
            others = sum(x.target==b and not x.carrying for x in self.workers if x.id!=w.id)
            crowd = sum(distance(x.pos,BERTHS[b])<=2 for x in self.workers if x.id!=w.id)
            risk = int(b in ('B1','B4') and self.is_risk(w))
            return .8*known[b] - 1.2*distance(w.pos,BERTHS[b]) - .8*others - .4*crowd - 100*risk + 3*(w.target==b)
        return max(available,key=lambda b:(score(b),b)) if available else None

    def move(self,w,dest,occupancy):
        if w.pos == dest:
            return
        p=w.pos
        adjacent=[(p[0]+1,p[1]),(p[0],p[1]-1),(p[0]-1,p[1]),(p[0],p[1]+1)]
        legal=[n for n in adjacent if 0<=n[0]<24 and 0<=n[1]<16 and occupancy[n]<3
               and not(n in (BERTHS['B1'],BERTHS['B4']) and self.is_risk(w))]
        reducing=[n for n in legal if distance(n,dest)<distance(p,dest)]
        if reducing:
            if self.routing=='spread':
                reducing.sort(key=lambda n:(occupancy[n],(n[0]+w.id)%3))
            step=reducing[0]
            occupancy[p]-=1; occupancy[step]+=1; w.pos=step
            return
        # BFS gives a legal shortest route; alternate equal-length choices relieve lanes.
        q = deque([w.pos]); first = {w.pos:None}
        while q:
            p = q.popleft()
            steps = [(p[0]+1,p[1]),(p[0],p[1]-1),(p[0]-1,p[1]),(p[0],p[1]+1)]
            if self.routing == 'spread':
                steps.sort(key=lambda n:(distance(n,dest),occupancy[n],(n[0]+w.id)%3))
            for n in steps:
                if not(0<=n[0]<24 and 0<=n[1]<16) or n in first or occupancy[n]>=3:
                    continue
                if n in (BERTHS['B1'],BERTHS['B4']) and self.is_risk(w):
                    continue
                first[n] = n if p==w.pos else first[p]
                if n==dest:
                    step = first[n]
                    occupancy[w.pos]-=1; occupancy[step]+=1; w.pos=step
                    return
                q.append(n)

    def advance(self):
        t = self.tick
        if t in self.arrivals:
            self.ships.append(Ship(len(self.ships)+1,t,self.units))
        if not self.closed:
            waiting = [s for s in self.ships if s.docked is None and s.held_until<=t]
            for b in BERTHS:
                if self.berths[b] is None and waiting:
                    s=waiting.pop(0); s.berth=b; s.docked=t; self.berths[b]=s.id
        if t%20==0:
            self.bulletin = {b:(self.ship(sid).cargo if sid else 0) for b,sid in self.berths.items()}
        if self.warning():
            for w in self.workers:
                w.remembers_until=t+20
        if t in self.storms:
            for w in self.workers:
                if w.pos in (BERTHS['B1'],BERTHS['B4']):
                    w.knocked_until=t+20; self.knockouts+=1
                    self.lost += int(w.carrying); w.carrying=False
        if self.controller is not None and t%20==0:
            self.controller.turn(self)
        occupancy = Counter(w.pos for w in self.workers)
        # Rotating first worker avoids a permanent ID-priority advantage.
        ordered = self.workers[t%self.nworkers:]+self.workers[:t%self.nworkers]
        for w in ordered:
            if self.policy=='baseline' or t<w.knocked_until:
                continue
            if w.carrying:
                if w.pos==WAREHOUSE:
                    self.delivered+=1; w.carrying=False; w.target=None
                else:
                    self.move(w,WAREHOUSE,occupancy)
                continue
            w.target=self.choose_target(w)
            if w.target is None:
                # On a warning evacuate unsafe cells, even if all berths are empty.
                if w.pos in (BERTHS['B1'],BERTHS['B4']) and self.is_risk(w):
                    self.move(w,(w.pos[0],2),occupancy)
                continue
            dest=BERTHS[w.target]
            if w.pos==dest:
                sid=self.berths[w.target]; s=self.ship(sid)
                if s and s.cargo>0 and s.held_until<=t:
                    s.cargo-=1; w.carrying=True
            else:
                self.move(w,dest,occupancy)
        for b,sid in list(self.berths.items()):
            s=self.ship(sid)
            if s and s.cargo==0:
                s.departed=t; self.berths[b]=None
        actual=Counter(w.pos for w in self.workers)
        self.violations += sum(n>3 for n in actual.values())
        for (x,y),n in actual.items():
            self.heat[y][x]+=n
        self.trace.append({'tick':t,'warehouse_queue':sum(distance(w.pos,WAREHOUSE)<=2 for w in self.workers),
                           'max_cell':max(actual.values()),'cargo':self.delivered,
                           'targets':dict(Counter(w.target for w in self.workers if w.target))})

    def run(self):
        for t in range(TICKS):
            self.tick=t; self.advance()
        # Restricted mean queue wait: include right-censored still-waiting ships.
        waits=[(s.docked if s.docked is not None else TICKS)-s.arrived for s in self.ships]
        result={'cargo_delivered':self.delivered,'avg_ship_wait':round(sum(waits)/len(waits),6) if waits else 0,
                'crowding_violations':self.violations,'storm_knockouts':self.knockouts}
        if self.controller:
            result.update(self.controller.metrics())
        return result
