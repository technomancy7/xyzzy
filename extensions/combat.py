import shlex
import re
import json

class Combat:
    def __init__(self, state):
        self.state = state
        self.writeln = self.state.writeln
        self.get_object = self.state.get_object
        self.trigger_object_event = self.state.trigger_object_event
        self.focus = self.state.focus

        self.participants = []

        self.victory_condition = "_.participants = 1"
        self.failure_condition = f"{self.state.focus}.health <= 0"

        self.victory_event = "print('You won!')"
        self.failure_event = "print('You died')"

    def check_battle_conditions(self):
        if self.victory_condition and self.handle_conditional(self.victory_condition):
            return 1

        if self.failure_condition and self.handle_conditional(self.failure_condition):
            return -1

        return 0

    def end_battle(self, end_type = 0):
        if end_type == 1 and self.victory_event:
            self.state._eval_code(self.victory_event)

        if end_type == -1 and self.failure_event:
            self.state._eval_code(self.failure_event)

        self.state.clear_scene()

    def __statusbar__(self):
        return f"In combat with {len(self.participants)} participants..."

    def handle_conditional(self, c):
        parts = shlex.split(c, " ")
        if "." in parts[0]:
            if parts[0] == "_.participants":
                first = len(self.participants)
            else:
                obj = self.get_object(parts[0].split(".")[0])

                first = obj.get(parts[0].split(".")[1])
        else:
            first = self.state.touch_var(parts[0])

        checker = parts[1]
        value = self.state._eval_code(parts[2])
        match checker:
            case "=" | "==":
                return first == value

            case ">":
                return first > value

            case "<":
                return first < value

            case ">=":
                return first >= value

            case "<=":
                return first <= value

        return False

    def __enter_scene__(self, *args, **kwargs):
        self.participants = [self.state.focus]
        for p in kwargs.get('targets', []):
            self.participants.append(p)
        self.state.rebuild_autocomplete()


    def __exit_scene__(self, *args, **kwargs):
        self.participants.clear()

    def __autocomplete__(self):
        player = self.state.get_object(self.state.focus)
        targets = [self.state.get_object(obj)['name'].split(" ")[0] for obj in self.participants]
        items = [self.state.get_object(obj)['name'].split(" ")[0] for obj in player['contains']]
        built = {}
        for t in targets:
            built[t] = None

        acd = {
            "use": {},
        }

        for item in items:
            acd['use'][item] = {
                "on": built
            }
            acd[item] = {
                "on": built
            }

        return acd

    def reduce_item(self, obj):
        if obj.get("uses", None) == None:
            return

        obj['uses'] -= 1
        if obj['uses'] <= 0 and "consumable" in obj['tags']:
            self.state.remove_actor(obj['id'])
            self.writeln(f"{obj['name']} is used up!")
        else:
            self.writeln(f"{obj['name']} has {obj['uses']} remaining.")

    def do_action(self, instigator, obj, target):
        act_type = obj.get("act_type", "")
        if obj.get("uses", None) != None and obj['uses'] <= 0:
            self.writeln(f"{obj['name']} has no uses remaining...")
            return
            
        match act_type:
            case "weapon":
                if obj.get("damages"):
                    pwr = obj['power']
                    target[obj['damages']] -= pwr


                    self.writeln(f"{target['name']} damaged by {pwr} {obj['damages']}. ({target[obj['damages']]})")
                    self.trigger_object_event(obj['id'], "combat_used", target = target['id'], instigator = self.focus)
                    if target[obj['damages']] <= 0:
                        self.writeln("Target dead.")
                        print(target['id'], "in", self.participants)
                        self.participants.remove(target['id'])
                        if "persists" not in target['tags']: self.state.remove_actor(target['id'])
                        self.trigger_object_event(target['id'], "combat_died", killed_by = obj['id'], instigator = self.focus)
                    else:
                        self.trigger_object_event(target['id'], "combat_hit", hit_by = obj['id'], instigator = self.focus)

                    self.reduce_item(obj)
                else:
                    self.writeln("Object not defined...")

            case "support":
                if obj.get("restores"):
                    pwr = obj['power']
                    target[obj['restores']] += pwr
                    limit = target.get("max_"+obj['restores'], 100)
                    if target[obj['restores']] > limit:
                        target[obj['restores']] = limit

                    self.trigger_object_event(obj['id'], "combat_used", target = target['id'], instigator = self.focus)
                    self.trigger_object_event(target['id'], "combat_supported", hit_by = obj['id'], instigator = self.focus)
                    self.writeln(f"{target['name']} restores {pwr} {obj['restores']}. ({target[obj['restores']]})")
                    self.reduce_item(obj)
                else:
                    self.writeln("Object not defined...")

            case "event":
                self.trigger_object_event(obj['id'], "combat_event", target = target['id'], instigator = instigator['id'])

            case _:
                self.writeln("Can't use that...")

        con = self.check_battle_conditions()
        if con != 0:
            self.end_battle(con)

    def read(self, line):
        player = self.state.get_object(self.state.focus)
        match line:
            case "i" | "inventory":
                for item in player['contains']:
                    obj = self.get_object(item)
                    txt = ""

                    if obj.get("power", None) != None:
                        txt = f"{txt} (Power: {obj['power']}"
                        if obj.get("restores"):
                            txt = f"{txt} {obj['restores']}"
                        txt = txt+")"

                    if obj.get("uses", None) != None:
                        txt = f"{txt} (Uses Remaining: {obj['uses']})"

                    if "consumable" in obj['tags']:
                        txt = f"{txt} (Consumable)"

                    self.writeln(f"{obj['name']}{txt}")
                return

            case "look" | "l" | "who":
                self.writeln(", ".join([f"{self.get_object(item)['name']} ({self.get_object(item)['health']})" for item in self.participants]))
                return


        opts = [self.state.get_object(obj) for obj in player['contains']]

        match = re.match(r'^(?:use\s+)?([\w\s]+?)(?:\s+on\s+)([\w\s]+)$', line)
        handled = False

        if match:
            object, target = match.groups()

            if target == "self" or target == "me":
                target = self.get_object(self.focus)['name']
            for obj in opts:
                if obj['name'].lower() == object.lower() or obj['name'].lower().split(" ")[0] == object.lower():
                    targets = [self.state.get_object(obj) for obj in self.participants]
                    for p in targets:
                        if p['name'].lower() == target.lower() or p['name'].lower().split(" ")[0] == target.lower():
                            self.do_action(player, obj, p)
                            handled = True

            self.state.rebuild_autocomplete()
            if not handled:
                self.state.writeln("What?")
            else:
                self.state.rebuild_autocomplete()
        else:
            self.state.writeln(f"Could not interpret intent...")


def __connect__():
    pass

XYZZY = {
    "scenes": [Combat],

}
