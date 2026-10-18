"""Read-only signal inventory. This cannot authorize or actuate priority."""
import hashlib
import json
import xml.etree.ElementTree as ET
from citybrain.chennai.network import NET


def audit():
    root=ET.parse(NET).getroot()
    signals=[]
    for logic in root.findall('tlLogic'):
        phases=[dict(p.attrib) for p in logic.findall('phase')]
        connections=[dict(c.attrib) for c in root.findall('connection') if c.get('tl')==logic.get('id')]
        indices={int(c['linkIndex']) for c in connections}
        width=max(len(p['state']) for p in phases)
        signals.append(dict(id=logic.get('id'),program=logic.get('programID'),type=logic.get('type'),
            phases=phases,controlled_connections=connections,
            unmapped_phase_indices=sorted(set(range(width))-indices),
            explicit_minimum_green=all('minDur' in p for p in phases),
            all_red_phases=[i for i,p in enumerate(phases) if set(p['state'])<={'r'}],
            movement_conflicts='NOT_REVIEWED',yellow_clearance='DURATIONS_PRESENT_NOT_SAFETY_VALIDATED',
            recovery_contract='NOT_VERIFIED',eligible_for_priority=False,
            status='ADVISORY_ONLY',required=['movement/conflict review','minimum-green contract',
                'movement-specific clearance/transition contract','cancellation/disappearance/exception/shutdown restoration verification']))
    return dict(network_sha256=hashlib.sha256(NET.read_bytes()).hexdigest(),signals=signals,
        actuation_implemented=False,comparative_priority_experiment='NOT_RUN — SAFETY GATE NOT SATISFIED')


if __name__=='__main__':
    print(json.dumps(audit(),indent=2))
