class BaseAgent:

    def __init__(self, name):
        self.name = name

    def run(self, state):
        raise NotImplementedError