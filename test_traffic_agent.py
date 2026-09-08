from citybrain.agents.traffic_agent import TrafficAgent


state = {
    "roads": {
        "E1": {
            "congestion": "LOW"
        },
        "E2": {
            "congestion": "MEDIUM"
        },
        "E5": {
            "congestion": "HIGH"
        }
    }
}


agent = TrafficAgent()

result = agent.run(state)

print("Traffic Agent:")
print(result)