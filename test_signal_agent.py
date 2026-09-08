from citybrain.agents.signal_agent import SignalAgent


state = {
    "roads": {
        "E1": {
            "from": "J1",
            "to": "J2"
        },
        "E2": {
            "from": "J2",
            "to": "J3"
        },
        "E6": {
            "from": "J8",
            "to": "J9"
        }
    }
}


route = ["E1", "E2", "E6"]


agent = SignalAgent()

result = agent.run(route, state)

print("Traffic Signal Agent:")
print("Signal priority:", result)