import shlex
import re
import json

class Combat:
    def __init__(self, state):
        self.state = state
        self.participants = []

    def __statusbar__(self):
        return f"In combat..."

    def handle_conditional(self, c):
        parts = shlex.split(c, " ")
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
                return first > value

            case "<=":
                return first < value

        return False

    def __enter_scene__(self, *args, **kwargs):
        self.participants = [self.state.focus]
        for p in kwargs.get('targets', []):
            self.participants.append(p)
        self.state.rebuild_autocomplete()
        print(self.participants)


    def __exit_scene__(self, *args, **kwargs):
        self.participants.clear()

    def __autocomplete__(self):
        player = self.state.get_object(self.state.focus)
        #loc = self.state.get_object(player['location'])

        targets = [self.state.get_object(obj)['name'].split(" ")[0] for obj in self.participants]


        items = [self.state.get_object(obj)['name'].split(" ")[0] for obj in player['contains']]
        #print("player contains", items)
        #print("loc contains", targets)
        #print("items", items)
        built = {}
        for t in targets:
            built[t] = None
        #print("built", built)
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
        #print(json.dumps(acd, indent=4))
        return acd

    def do_action(self, obj, target):
        print("doing", obj, target)

    def read(self, line):
        player = self.state.get_object(self.state.focus)
        opts = [self.state.get_object(obj) for obj in player['contains']]

        #matches = re.findall(, line)
        match = re.match(r'^(?:use\s+)?([\w\s]+?)(?:\s+on\s+)([\w\s]+)$', line)
        handled = False

        if match:
            object, target = match.groups()
            #print(f"Matched: Object: '{object}', Target: '{target}'")
            for obj in opts:
                if obj['name'].lower() == object.lower() or obj['name'].lower().split(" ")[0] == object.lower():
                    #print("USING", obj)
                    targets = [self.state.get_object(obj) for obj in self.participants]
                    for p in targets:
                        if p['name'].lower() == target.lower() or p['name'].lower().split(" ")[0] == target.lower():
                            self.do_action(obj, p)
                            handled = True
            self.state.rebuild_autocomplete()
            if not handled:
                self.state.writeln("What?")
        else:
            self.state.writeln(f"Could not interpret intent...")


def __connect__():
    pass

XYZZY = {
    "scenes": [Combat],

}
