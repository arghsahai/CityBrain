"""Build a small 3x4 extension; preserve the original 3x3 regression assets."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import sumolib

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT/'simulation/network/research'

def build():
    RESEARCH.mkdir(parents=True, exist_ok=True)
    nodes = ET.parse(ROOT/'simulation/network/regression/city.nod.xml')
    edges = ET.parse(ROOT/'simulation/network/regression/city.edg.xml')
    for node, x in [('J10',0), ('J11',100), ('J12',200)]:
        ET.SubElement(nodes.getroot(), 'node', id=node, x=str(x), y='300', type='traffic_light')
    pairs = [('J7','J10'), ('J8','J11'), ('J9','J12'), ('J10','J11'), ('J11','J12')]
    for index, (start, end) in enumerate(pairs):
        for offset, source, target in [(0,start,end),(1,end,start)]:
            ET.SubElement(edges.getroot(), 'edge', {'id':f'E{25+2*index+offset}', 'from':source,
                                                  'to':target,'numLanes':'1','speed':'13.9'})
    nodes.write(RESEARCH/'city.nod.xml', encoding='utf-8', xml_declaration=True)
    edges.write(RESEARCH/'city.edg.xml', encoding='utf-8', xml_declaration=True)
    subprocess.run([sumolib.checkBinary('netconvert'), '-n',str(RESEARCH/'city.nod.xml'),
                    '-e',str(RESEARCH/'city.edg.xml'), '-o',str(RESEARCH/'city.net.xml')],check=True)

if __name__ == '__main__':
    build()
