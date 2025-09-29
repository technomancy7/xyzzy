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

    # Events
    def on_heal(self, healing, healed_by):
        return None

    def on_hit(self, damage, hit_by):
        return None

    def on_talk(self):
        return None

    def on_death(self):
        return None

    # Methods
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
        if self.health <= 0: return self.health

        self.health = self.health - damage

        if self.health <= 0:
            self.on_death()

        return self.health

    def heal(self, v, healed_by = None) -> int: #TODO check if self has function on_heal and trigger that
        self.health = self.health + v

        if self.health > self.health_max:
            self.health = self.health_max

        self.on_heal(v, healed_by)

        return self.health

class HumanNPC(Human):
    pass

class XyzzyZone(XyBase):
    def __init__(self, state):
        super().__init__(state)
        state.tree["zones"][self.xyname()] = self
        self.contains = {}

    def __repr__(self):
        return self.name

    def remove_item(self, item):
        self.contains[item.xyname()] = self.contains[item.xyname()] - 1
        if self.contains[item.xyname()] <= 0:
            del self.contains[item.xyname()]

    def add_item(self, item):
        if not self.contains.get(item.xyname()):
            self.contains[item.xyname()] = 0
        self.contains[item.xyname()] = self.contains[item.xyname()] + 1

    def exit_north(self):
        return None

    def exit_east(self):
        return None

    def exit_south(self):
        return None

    def exit_west(self):
        return None

    def exit_up(self):
        return None

    def exit_down(self):
        return None

    def exit_in(self):
        return None

    def exit_out(self):
        return None
