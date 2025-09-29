class XyBase:
    __ignore_keys__ = ["state"]
    def __init__(self, state):
        self.state = state

    def xyname(self):
        return self.__class__.__name__

    def loadxyd(self, d):
        self.__dict__.update(d)

    def xydata(self):
        d = self.__dict__.copy()
        for key in self.__ignore_keys__:
            del d[key]

        return d

class XyzzyObject(XyBase):
    def __init__(self, state):
        super().__init__(state)
        state.tree["objects"][self.xyname()] = self

    def __repr__(self):
        return f"? {self.name}"

class InventoryItem(XyzzyObject):
    def __init__(self, state):
        super().__init__(state)

    def __repr__(self):
        return f"* {self.name}"

    def on_use(self, target = None):
        pass

class Consumable(InventoryItem):
    pass

class Human(XyzzyObject):
    def __init__(self, state):
        super().__init__(state)
        self.health = 100
        self.health_max = 100
        self.invincible = False
        self.inventory = {}
        self.say_colour = "red"

    def __repr__(self):
        return f"@ {self.name} ({self.health} HP)"

    def say(self, text):
        c = self.state.sh.c
        self.state.log(f"{c(self.say_colour)}{text}{c('reset')}", f"{c(self.say_colour)}{self.name}{c('reset')}")

    def remove_item(self, item):
        self.inventory[item.xyname()] = self.inventory[item.xyname()] - 1
        if self.inventory[item.xyname()] <= 0:
            del self.inventory[item.xyname()]

    def add_item(self, item):
        if not self.inventory.get(item.xyname()):
            self.inventory[item.xyname()] = 0
        self.inventory[item.xyname()] = self.inventory[item.xyname()] + 1

    def is_dead(self):
        return self.health <= 0

    def take_damage(self, damage, instigator = None) -> int:
        self.health = self.health - damage

        return self.health

    def heal(self, heal_by, healed_by = None) -> int: #TODO check if self has function on_heal and trigger that
        self.health = self.health + heal_by

        if self.health > self.health_max:
            self.health = self.health_max

        return self.health

class HumanNPC(Human):
    pass

class XyzzyZone(XyBase):
    def __init__(self, state):
        super().__init__(state)
        state.tree["zones"][self.xyname()] = self
        self.contains = {}

    def remove_item(self, item):
        self.contains[item.xyname()] = self.contains[item.xyname()] - 1
        if self.contains[item.xyname()] <= 0:
            del self.contains[item.xyname()]

    def add_item(self, item):
        if not self.contains.get(item.xyname()):
            self.contains[item.xyname()] = 0
        self.contains[item.xyname()] = self.contains[item.xyname()] + 1
