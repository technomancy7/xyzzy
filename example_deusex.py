from xyobjects import *

def story():
    return {
        "save_id": "dxd",
        "title": "Deus Ex: DE-MAKE test",
        "author": "Technomancer",
        "player": "jcd",
        "start": "liberty_docks"
    }

def on_start(state):
    state.log("Talk to paul.", "Goal Updated")

class liberty_docks(XyzzyZone):
    def __init__(self, state):
        super().__init__(state)
        self.name = "Liberty Island (Docks)"
        self.contains = {"medkit": 2}


class medkit(Consumable):
    def __init__(self, state):
        super().__init__(state)
        self.name = "medkit"
        self.power = 25

    def on_use(self, target = None):
        if target:
            target.heal(self.power)

class paul(HumanNPC):
    def __init__(self, state):
        super().__init__(state)
        self.name = "Paul Denton"


class jcd(Human):
    def __init__(self, state):
        super().__init__(state)
        self.name = "JC Denton"


