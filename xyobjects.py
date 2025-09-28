class XyBase:
    __ignore_keys__ = ["state"]

    def loadxyd(self, d):
        self.__dict__.update(d)

    def xydata(self):
        d = self.__dict__.copy()
        for key in self.__ignore_keys__:
            del d[key]
        return d

class XyzzyObject(XyBase):
    def __init__(self, state):
        self.state = state
        state.tree["objects"][self.__class__.__name__] = self

class InventoryItem(XyzzyObject):
    def __init__(self, state):
        super().__init__(state)
        self.count = 0

    def on_use(self, target = None):
        pass

class Consumable(InventoryItem):
    pass

class Human(XyzzyObject):
    def __init__(self, state):
        super().__init__(state)
        self.health = 100
        self.health_max = 100
        self.inventory = {}

    def heal(self, heal_by, healed_by = None) -> int: #TODO check if self has function on_heal and trigger that
        self.health = self.health + heal_by

        if self.health > self.health_max:
            self.health = self.health_max

        return self.health

class HumanNPC(Human):
    pass

class XyzzyZone(XyBase):
    def __init__(self, state):
        self.state = state
        state.tree["zones"][self.__class__.__name__] = self
        self.contains = {}
