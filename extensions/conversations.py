
class Convo:
    def __init__(self, state):
        self.state = state

        self.participants = []

    def __enter_scene__(self):
        print("Entered convo")

    def __exit_scene__(self):
        print("Left convo")

    def read(self, line):
        print(line)

        if line == "end":
            self.state.clear_scene()

XYZZY = {
    "scenes": [Convo]
}
