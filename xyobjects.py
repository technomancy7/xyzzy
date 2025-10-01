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
        self.name = ""

    def __repr__(self):
        return f"? {self.name}"

class InventoryItem(XyzzyObject):
    def __init__(self, state):
        super().__init__(state)

        # A helper flag to tell the interpreter to ask for a target
        self.require_target = False

        # A generic stat value that can easily define how powerful it's effect is
        self.base_power = 0

        # Deduct count by 1 when used
        self.one_use = False

    def __repr__(self):
        return f"* {self.name}"

    # Calculate power formula, can be overridden in subclasses to create new calculations
    def power(self):
        return self.base_power

    # Events
    def on_use(self, target = None):
        pass

    # Can this item be moved to/from inventory
    def is_inventory_locked(self):
        return False

class Consumable(InventoryItem):
    def __init__(self, state):
        super().__init__(state)
        self.one_use = True


class Decoration(XyzzyObject):
    def __init__(self, state):
        super().__init__(state)
        self.health = 100
        self.invincible = False
        self.contents = {}

    def __repr__(self):
        return f"# {self.name} ({self.health} HP)"

    # Events
    def on_hit(self, damage, hit_by):
        return None

    def on_break(self, broken_by = None):
        self.state.log("Broken, dropping inventory...", self.name)
        for k, v in self.contents.items():
            #self.remove_item(k, v)
            self.state.location.add_item(k, v)
            self.state.log(f"{k} x{v}", "dropped")
        self.content = {}

    # Methods
    def get_item_count(self, item):
        if self.state.isof(item, XyzzyObject):
            return self.contents.get(item.xyname(), 0)
        else:
            return self.contents.get(item, 0)

    def has_item(self, item):
        if self.state.isof(item, XyzzyObject):
            return self.contents.get(item.xyname()) != None
        else:
            return self.contents.get(item) != None

    def remove_item(self, item, count = 1):
        if self.state.isof(item, XyzzyObject):
            item = item.xyname()

        if count > self.contents[item]: count = self.contents[item]

        self.contents[item] = self.contents[item] - count
        if self.contents[item] <= 0:
            del self.contents[item]

    def add_item(self, item, count = 1):
        if self.state.isof(item, XyzzyObject):
            item = item.xyname()

        if not self.contents.get(item):
            self.contents[item] = 0
        self.contents[item] = self.contents[item] + count

    def is_broken(self):
        return self.health <= 0

    def take_damage(self, damage, instigator = None) -> int:
        if self.health <= 0: return self.health

        if self.invincible:
            return

        self.health = self.health - damage

        self.on_hit(damage, instigator)

        if self.health <= 0:
            self.on_break(instigator)

        return self.health




class Pawn(XyzzyObject):
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

    def on_death(self, killed_by = None):
        return None


    # Methods
    def say(self, text):
        c = self.state.sh.c
        self.state.log(f"{c(self.say_colour)}{text}{c('reset')}", f"{c(self.say_colour)}{self.name}{c('reset')}")

    def get_item_count(self, item):
        if self.state.isof(item, XyzzyObject):
            return self.inventory.get(item.xyname(), 0)
        else:
            return self.inventory.get(item, 0)

    def has_item(self, item):
        if self.state.isof(item, XyzzyObject):
            return self.inventory.get(item.xyname()) != None
        else:
            return self.inventory.get(item) != None

    def remove_item(self, item, count = 1):
        if self.state.isof(item, XyzzyObject):
            item = item.xyname()

        if count > self.inventory[item]: count = self.inventory[item]

        self.inventory[item] = self.inventory[item] - count
        if self.inventory[item] <= 0:
            del self.inventory[item]

    def add_item(self, item, count = 1):
        if self.state.isof(item, XyzzyObject):
            item = item.xyname()

        if not self.inventory.get(item):
            self.inventory[item] = 0
        self.inventory[item] = self.inventory[item] + count

    def is_dead(self):
        return self.health <= 0

    def take_damage(self, damage, instigator = None) -> int:
        if self.health <= 0: return self.health

        if self.invincible:
            return

        self.health = self.health - damage

        self.on_hit(damage, instigator)

        if self.health <= 0:
            self.on_death(instigator)

        return self.health

    def heal(self, v, healed_by = None) -> int:
        self.health = self.health + v

        if self.health > self.health_max:
            self.health = self.health_max

        self.on_heal(v, healed_by)

        return self.health


class Animal(Pawn):
    pass

class Human(Pawn):
    pass

class HumanNPC(Human):
    pass






class XyzzyZone(XyBase):
    def __init__(self, state):
        super().__init__(state)
        state.tree["zones"][self.xyname()] = self
        self.contains = {}

    def __repr__(self):
        return self.name

    def has_item(self, item):
        if self.state.isof(item, XyzzyObject):
            return self.contains.get(item.xyname()) != None
        else:
            return self.contains.get(item) != None

    def remove_item(self, item, count = 1):
        if self.state.isof(item, XyzzyObject):
            item = item.xyname()

        if count > self.contains[item]: count = self.contains[item]

        self.contains[item] = self.contains[item] - count
        if self.contains[item] <= 0:
            del self.contains[item]

    def add_item(self, item, count = 1):
        if self.state.isof(item, XyzzyObject):
            item = item.xyname()

        if not self.contains.get(item):
            self.contains[item] = 0
        self.contains[item] = self.contains[item] + count

    def get_exit(self, direction):
        return getattr(self, f"exit_{direction}")()

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
