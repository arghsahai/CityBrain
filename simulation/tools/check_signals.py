"""Read SUMO signal infrastructure and verify reversible phase control."""
import sumolib
import traci
from experiments.runners.compare import ROOT

def main():
    traci.start([sumolib.checkBinary('sumo'), '-c', str(ROOT/'simulation/network/regression/city.sumocfg'), '--no-step-log', 'true'])
    try:
        traci.simulationStep()
        signals = traci.trafficlight.getIDList()
        if not signals:
            raise RuntimeError('Network has no traffic signals')
        for signal in signals:
            phase = traci.trafficlight.getPhase(signal)
            links = traci.trafficlight.getControlledLinks(signal)
            state = traci.trafficlight.getRedYellowGreenState(signal)
            logic = traci.trafficlight.getAllProgramLogics(signal)[0]
            test_phase = (phase + 1) % len(logic.phases)
            traci.trafficlight.setPhase(signal, test_phase)
            assert traci.trafficlight.getPhase(signal) == test_phase
            traci.trafficlight.setPhase(signal, phase)
            print(signal, state, 'controlled links:', len(links))
    finally:
        traci.close()

if __name__ == '__main__':
    main()
