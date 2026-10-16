"""Read frozen artifacts and generate derived presentation tables/figures only."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import statistics as stats
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/krishna'
PROFILES = ['normal', 'heavy', 'peak']


def table(headers, rows):
    def cell(v): return str(v).replace('|', '/').replace('\n', ' ')
    return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(map(cell,r))+' |\n' for r in rows)+'\n'


def number(x): return 'Unavailable' if x is None else f'{x:.2f}'
def describe(xs):
    return [number(stats.mean(xs)) if xs else 'Unavailable', number(stats.median(xs)) if xs else 'Unavailable', number(stats.stdev(xs)) if len(xs)>1 else 'Unavailable']


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources=['validation_matrix.csv','s08_validation.csv']
    datasets=[list(csv.DictReader((ROOT/'experiments/results'/f).open())) for f in sources]
    rows=sum(datasets, [])
    expected=set(itertools.product(['S05','S07','S08'], PROFILES, map(str,range(1,11)), ['static','dynamic']))
    keys=[(r['scenario'],r['profile'],r['seed'],r['strategy']) for r in rows]
    if len(keys)!=180 or set(keys)!=expected: raise ValueError('Trial identities differ from expected 180')
    # Compare actual paired route inputs and checkpoints; do not run SUMO.
    for r in rows:
        folder='s08-official-v2' if r['scenario']=='S08' else 'matrix-'+r['profile']
        base=ROOT/'experiments/results'/folder
        ident=f"{r['scenario']}_{r['profile']}_{r['seed']}_"
        if (base/(ident+'static')/'routes.rou.xml').read_bytes() != (base/(ident+'dynamic')/'routes.rou.xml').read_bytes():
            raise ValueError('Pair demand differs')
        if (base/(ident+'static')/'run.sumocfg').read_bytes() != (base/(ident+'dynamic')/'run.sumocfg').read_bytes():
            raise ValueError('Pair SUMO configuration differs')
        checkpoint=json.loads((base/(ident+r['strategy'])/'result.json').read_text())
        for field in ('completion_status','initial_route','final_route','successful_route_changes','actual_travel_time'):
            if str(checkpoint[field]) != r[field]: raise ValueError(f'Aggregate mismatch: {ident} {field}')
    from experiments.analysis.s08 import audit
    _,_,applied=audit(ROOT/'experiments/results/s08-official-v2')
    counts=[];success=[];travel=[];failures=[];distribution=[];latencies=[]
    groups={}
    for scenario,profile,mode in itertools.product(['S05','S07','S08'],PROFILES,['static','dynamic']):
        group=[r for r in rows if (r['scenario'],r['profile'],r['strategy'])==(scenario,profile,mode)]
        groups[(scenario,profile,mode)]=group
        good=[r for r in group if r['completion_status']=='SUCCESS']
        success.append([scenario,profile,mode,f'{len(good)}/{len(group)}',f'{100*len(good)/len(group):.1f}%'])
        xs=[float(r['actual_travel_time']) for r in good]
        travel.append([scenario,profile,mode,f'{len(good)}/{len(group)}',*describe(xs),number(min(xs)) if xs else 'Unavailable',number(max(xs)) if xs else 'Unavailable'])
        bad={o:sum(r['completion_status']==o for r in group) for o in ['TELEPORTED','ERROR','TIMEOUT','NO_ROUTE','FAILED_BLOCKED']}
        failures.append([scenario,profile,mode,len(group),*bad.values()])
    for p,m in itertools.product(PROFILES,['static','dynamic']):
        g=groups[('S08',p,m)];freq=[sum(int(r['successful_route_changes'])==n for r in g) for n in [0,1]]
        distribution.append([p,m,len(g),*freq,sum(int(r['successful_route_changes'])>=2 for r in g)])
        xs=[a['simulation_latency'] for a in applied if a['profile']==p and a['strategy']==m]
        latencies.append([p,m,len(xs),*describe(xs),number(min(xs)) if xs else 'Unavailable',number(max(xs)) if xs else 'Unavailable'])
    sections=[('1. Trial-count audit',['Dataset','Scenarios','Profiles','Seeds','Modes','Trials','Matched pairs'],[['PR #3 baseline','S05 + S07',3,10,2,120,60],['PR #4 official V2','S08',3,10,2,60,30],['Inventory total (not pooled effect)','3 scenario families',3,10,2,180,90]]),
      ('2. Success rates',['Scenario','Profile','Mode','Success/all trials','Rate'],success),
      ('3. Successful emergency travel time (seconds)',['Scenario','Profile','Mode','Successful/all','Mean','Median','Sample SD','Min','Max'],travel),
      ('4. Failure counts (all-trial denominators)',['Scenario','Profile','Mode','N','TELEPORTED','ERROR','TIMEOUT','NO_ROUTE','FAILED_BLOCKED'],failures),
      ('5. S08 replanning frequency (all trials)',['Profile','Mode','N','0 changes','1 change','2+ changes'],distribution),
      ('6. S08 applied latency (simulation seconds; denominator = applications)',['Profile','Mode','Applications','Mean','Median','Sample SD','Min','Max'],latencies)]
    text='# Final research result tables\n\nDerived without rerunning trials. Sources: `experiments/results/validation_matrix.csv`, `s08_validation.csv`, and audited S08 V2 per-trial events. Successful-only timing is conditional on arrival; failure denominators always include all trials. SD is sample SD (n−1). No static S08 travel comparison is possible.\n\n'
    for title,headers,data in sections:text+='## '+title+'\n\n'+table(headers,data)
    comparisons=[]
    for p in PROFILES:
        a=groups[('S07',p,'static')];b=groups[('S07',p,'dynamic')]
        ma=stats.mean(float(r['actual_travel_time']) for r in a);mb=stats.mean(float(r['actual_travel_time']) for r in b)
        comparisons.append([p,'10/10',number(ma),number(mb),number(ma-mb),f'{100*(ma-mb)/ma:.2f}%'])
    text+='## S07 matched-success comparison\n\n'+table(['Profile','Jointly successful pairs','Static mean s','Dynamic mean s','Mean difference s','Reduction in group mean'],comparisons)
    text+='Percentages are descriptive reductions in the group mean, not a significance test or a mean of per-seed percentages. S05 jointly successful pairs have zero travel-time difference; its gain is reliability. S08 has zero jointly successful pairs.\n'
    (OUT/'RESULT_TABLES.md').write_text(text)
    # Complete network tables from compiled files, including real lane lengths.
    text='# Network inventory\n\nThe active research baseline is regression/, not the retained initial team network at simulation/network/. Coordinates are synthetic metres. Each road pair is two directed edges; internal junction edges are excluded from counts.\n\n'
    for name in ['regression','research']:
        path=ROOT/'simulation/network'/name
        net=ET.parse(path/'city.net.xml');nodes=ET.parse(path/'city.nod.xml');edges=[e for e in net.findall('edge') if not e.get('id').startswith(':')]
        tls=[t.get('id') for t in net.findall('tlLogic')]
        text+=f'## {name}: {len(nodes.findall("node"))} junctions, {len(edges)} directed external edges, {len(tls)} signal programs\n\n'
        text+=table(['Junction','x (m)','y (m)','Configured type','Compiled signal'],[[n.get('id'),n.get('x'),n.get('y'),n.get('type'),n.get('id') in tls] for n in nodes.findall('node')])
        text+=table(['Edge','From','To','Lanes','Speed m/s','Lane length m'],[[e.get('id'),e.get('from'),e.get('to'),len(e.findall('lane')),e.find('lane').get('speed'),e.find('lane').get('length')] for e in sorted(edges,key=lambda e:int(e.get('id')[1:]))])
    text+='''## Text topology and hospital

```text
Research extension: J10 ↔ J11 ↔ J12
                      ↕     ↕     ↕
Regression top row:  J7  ↔  J8  ↔  J9 (H1)
                      ↕     ↕     ↕
                     J4  ↔  J5  ↔  J6
                      ↕     ↕     ↕
                     J1  ↔  J2  ↔  J3
```

Ambulance departs at J1 on E13 at scheduled time 300; observed dispatch is 301.
The research emergency object labels the incident J3. Routing here models transport to
H1/J9, not a complete dispatch-to-patient-to-hospital workflow. H1 is configured metadata,
not a physical hospital building or live bed feed. Regression incoming hospital edges are
E11 and E23; the research extension adds E30 from J12. All hospital availability is static.
S08 adds ten edges E25–E34 and J10–J12 to offer a bypass after E7/E11 disruption.
'''
    demand = ET.parse(ROOT/'simulation/scenarios/S05_dynamic_blockage/dynamic_blockage.rou.xml')
    text+='\n## Base demand route catalogue\n\n'+table(['Route ID','Directed edge sequence'], [[r.get('id'),r.get('edges')] for r in demand.findall('route')])
    text+='\nThese declared routes are not all active background flows. The four actual flows use normalRoute3/4/5/7. The historical emergency candidate catalogue R_EM_1–4 is defined in citybrain/integration/state_adapter.py; S08 research adds R_EM_5 explicitly. The integrated runtime can instead generate live topology candidates.\n'
    (OUT/'NETWORK.md').write_text(text)
    # Git-based per-file contribution evidence, not ownership inferred from directory.
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only','origin/main','--','simulation','experiments','docs/INTEGRATION.md','docs/S08_VALIDATION_PROTOCOL.md','docs/S08_VALIDATION_RESULTS.md','citybrain/integration/state_adapter.py'],cwd=ROOT,text=True).splitlines()
    entries=[]
    for path in paths:
        history=subprocess.check_output(['git','log','origin/main','--format=%h %an <%ae> %s','--',path],cwd=ROOT,text=True).splitlines()
        authored=[h for h in history if 'krishna.verma2025@vitstudent.ac.in' in h and 'Merge pull request' not in h]
        purpose=('Experiment runner/audit/analysis' if path.endswith('.py') and path.startswith('experiments/') else 'Network/topology' if '/network/' in path else 'Scenario/demand/config' if path.startswith('simulation/') else 'Research evidence/documentation')
        entries.append([path,purpose,'; '.join(authored) if authored else 'No Krishna-authored change in unified history', 'Tracked on frozen main; preserved', 'Experiment workflow / report' if path.startswith(('experiments/','docs/')) else 'SUMO / scenario runner',history[-1] if history else 'Unknown'])
    (OUT/'CONTRIBUTION_MAP.md').write_text('# KRISHNA CONTRIBUTION MAP\n\nCommit attribution is evidence of authorship, not a claim of exclusive intellectual ownership. Initial SUMO assets were authored by Argh; Krishna ported the regression assets and built experimental tooling in the unified history. The final runtime/hotfix commits also carry Krishna’s authorship and should be acknowledged as integration work, while Argh owns the original Core architecture and Subhashini the planner.\n\n'+table(['File/module','Purpose','Krishna-authored contribution commits','Current status','Used by','Earliest recorded commit/author'],entries))
    # Provenance plus transparent derivation checks.
    provenance=dict(authoritative_main=subprocess.check_output(['git','rev-parse','origin/main'],cwd=ROOT,text=True).strip(),trial_counts=[len(x) for x in datasets],unique_identities=len(set(keys)),matched_input_pairs=90,matched_config_pairs=90,s08_applied_routes_audited=len(applied),sources={str(ROOT/'experiments/results'/f):hashlib.sha256((ROOT/'experiments/results'/f).read_bytes()).hexdigest() for f in sources})
    (OUT/'AUDIT.json').write_text(json.dumps(provenance,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
    figdir=OUT/'figures';figdir.mkdir(exist_ok=True)
    labels=[s+'\n'+p for s,p in itertools.product(['S05','S07','S08'],PROFILES)]
    keys=list(itertools.product(['S05','S07','S08'],PROFILES));colors={'static':'#60758c','dynamic':'#008c81'}
    for metric,name,title in [('success','01_success','Success across all trials'),('time','02_travel','Travel time conditional on successful arrival')]:
        fig,ax=plt.subplots(figsize=(12,5))
        for j,m in enumerate(['static','dynamic']):
            vals=[]
            for s,p in keys:
                g=groups[(s,p,m)];good=[float(r['actual_travel_time']) for r in g if r['completion_status']=='SUCCESS']
                vals.append(100*len(good)/len(g) if metric=='success' else stats.mean(good) if good else float('nan'))
            bars=ax.bar([i+(j-.5)*.36 for i in range(len(keys))],vals,.36,label=m.title(),color=colors[m])
            for bar,(s,p),value in zip(bars,keys,vals):
                g=groups[(s,p,m)];n=sum(r['completion_status']=='SUCCESS' for r in g)
                if value==value:ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+1.5,f'{n}/10',ha='center',fontsize=8)
                else:ax.text(bar.get_x()+bar.get_width()/2,3,'No\nsuccess',ha='center',fontsize=8)
        ax.set_xticks(range(len(keys)),labels);ax.set_ylabel('Success (%)' if metric=='success' else 'Mean travel time (s)');ax.set_ylim(0,118 if metric=='success' else 145);ax.set_title(title);ax.legend();fig.tight_layout();fig.savefig(figdir/(name+'.png'));plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5))
    for m in ['static','dynamic']:
        ax.plot(PROFILES,[stats.mean(float(r['actual_travel_time']) for r in groups[('S07',p,m)]) for p in PROFILES],marker='o',lw=2,color=colors[m],label=m.title())
    ax.set_ylabel('Mean successful travel time (s)');ax.set_title('S07 demand sensitivity — 10/10 successes per cell');ax.legend();fig.tight_layout();fig.savefig(figdir/'03_profiles.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5));bottom=[0]*3
    for n,color in [(0,'#60758c'),(1,'#edb54f'),(2,'#008c81')]:
        vals=[sum(int(r['successful_route_changes'])==n for r in groups[('S08',p,'dynamic')]) for p in PROFILES]
        ax.bar(PROFILES,vals,bottom=bottom,label=f'{n} replans',color=color);bottom=[a+b for a,b in zip(bottom,vals)]
    ax.set_ylabel('Trials (N = 10 per profile)');ax.set_title('S08 dynamic route-change frequency');ax.legend();fig.tight_layout();fig.savefig(figdir/'04_replans.png');plt.close(fig)
    log=ROOT/'data/output/integration/exception-safety-hotfix-smokes/S08/runtime/events.jsonl'
    events=[json.loads(l) for l in log.read_text().splitlines()]
    points=[e for e in events if e['action'] in ('PLAN_ACCEPTED','REPLAN_ACCEPTED','TERMINAL')]
    fig,ax=plt.subplots(figsize=(11,3));times=[e['simulation_time'] for e in points]
    ax.plot(times,[0]*len(times),'o-',color='#008c81')
    for i,e in enumerate(points):
        label=e['terminal_outcome'] if e['action']=='TERMINAL' else 'P'+str(e['accepted_plan']['revision'])
        ax.annotate(f'{label}\n{e["simulation_time"]:.0f} s',(e['simulation_time'],0),xytext=(0,30 if i%2==0 else -45),textcoords='offset points',ha='center')
    ax.set_ylim(-1,1);ax.set_yticks([]);ax.set_xlabel('Simulation time (s)');ax.set_title('Final integrated S08 smoke — separate from the 60 research trials');fig.tight_layout();fig.savefig(figdir/'05_timeline.png');plt.close(fig)
    print(json.dumps(provenance,indent=2))


if __name__=='__main__': main()
