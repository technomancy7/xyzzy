import sys, os, importlib, cmd, readline, json
from xyobjects import Human, InventoryItem
story_path = os.path.expanduser("~/.xyzzy-stories")
sys.path.append(story_path)

class XySh(cmd.Cmd):
    intro = 'Welcome to Xyzzy. Type LOAD followed by a story name to begin.\n'
    prompt = '(No story loaded) '
    response_handler = None
    ansi_colours = {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "bright_black": "\033[90m",
        "bright_red": "\033[91m",
        "bright_green": "\033[92m",
        "bright_yellow": "\033[93m",
        "bright_blue": "\033[94m",
        "bright_magenta": "\033[95m",
        "bright_cyan": "\033[96m",
        "bright_white": "\033[97m",
        "reset": "\033[0m"
    }

    def c(self, name = "reset"):
        return self.ansi_colours.get(name, "\033[0m")

    def set_xy(self, state):
        self.state = state
        self.state.sh = self

    def do_pass(self, line):
        pass

    def precmd(self, line):
        if self.response_handler != None:
            if not self.response_handler(line):
                self.response_handler = None
                return "pass"
            return ""
        return line

    def _select(self, opts, callback):
        if len(opts) == 0:
            self.state.log("Nothing found", "world")

        elif len(opts) == 1:
            try:
                callback(opts[list(opts.keys())[0]])
            except Exception as e:
                self.state.log(f"{e}", "error")

        else:
            def _filter(l):
                try:
                    callback(opts[list(opts.keys())[int(l)]])
                except Exception as e:
                    self.state.log(f"{e}", "error")

            self.state.log("> Select one:", "choice")
            for i, key in enumerate(opts.keys()):
                m = opts[key]
                self.state.log(m, f"{i}")

            self.response_handler = _filter

    def do_shell(self, arg):
        if arg.startswith("!"):
            os.system(arg[1:])
        else:
            try:
                eval(compile(arg, "<string>", "eval"), {
                    "sh": self,
                    "state": self.state,
                    "player": self.state.player,
                    "location": self.state.location,
                    "log": self.state.log
                })
            except Exception as e:
                print(e)

    def do_say(self, arg):
        self.state.player.say(arg)

    def do_drop(self, item_name):
        """Drops item from inventory in to current location"""
        opts = self.state._find_matches(item_name, self.state.player.inventory)

        def actual_take(target):
            if self.state.isof(target, InventoryItem):
                self.state.player.remove_item(target)
                self.state.location.add_item(target)
                self.state.log(target.name, "drop")

        self._select(opts, actual_take)

    def do_take(self, item_name):
        """Takes an item from the current location"""
        opts = self.state._find_matches(item_name)

        def actual_take(target):
            if self.state.isof(target, InventoryItem):
                self.state.location.remove_item(target)
                self.state.player.add_item(target)
                self.state.log(target.name, "take")

        self._select(opts, actual_take)

    def do_talk(self, item_name):
        pass
        """
        TODO
        opposite of take

        """

    def do_move(self, direction):
        l = self.state.location
        if hasattr(l, f"exit_{direction}"):
            e = getattr(l, f"exit_{direction}")
            self.state.location = self.state.getcls(e()['name'])
            self.state.log(f"Entering {self.state.location.name}")
        else:
            self.state.log("There is nothing there.")

    def do_hit(self, arg):
        opts = self.state._find_matches(arg)

        def actual_hit(target):
            target.take_damage(10, "player")
            self.state.log(f"{target.name}", "hit")

        self._select(opts, actual_hit)

    def do_inventory(self, arg):
        for k, v in self.state.player.inventory.items():
            item = self.state.getcls(k)
            self.state.log(f"{item.name} x{v}", "inventory")

    def do_look(self, arg):
        self.state.log(f"You are in {self.state.location.name}")
        for d in self.state.directions:
            if hasattr(self.state.location, f"exit_{d}"):
                e = getattr(self.state.location, f"exit_{d}")()
                ex = self.state.getcls(e['name'])
                self.state.log(f"To the {d} is {ex}", "world")

        self.state.log(f"Player Health: {self.state.player.health}", "look")
        for key, count in self.state.location.contains.items():
            c = self.state.getcls(key)
            if self.state.isof(c, Human):
                self.state.log(f"{c}", "look")
            elif self.state.isof(c, InventoryItem):
                self.state.log(f"{c} x{count}", "look")
            else:
                self.state.log(f"{c} x{count}", "look")

    def do_save(self, arg):
        self.state.export_state(arg or "save")

    def do_start(self, args):
        sc = False
        if " " in args:
            sc = self.state.init_story(args.split(" ")[0], args.split(" ")[1])
        else:
            sc = self.state.init_story(args)
        if sc:
            self.prompt = f"(> "
            if hasattr(self.state.story, "on_start"):
                self.state.story.on_start(self.state)

class XyState:
    def __init__(self):
        self.tree = {"zones": {}, "objects": {}}
        self.directions = ["north", "south", "east", "west", "up", "down", "in", "out"]
        self.reverse_directions = {
            "north": "south", "south": "north",
            "east": "west", "west": "east",
            "up": "down", "down": "up",
            "in": "out", "out": "in"
        }
        self.story = None
        self.sh = None

        self.player = None
        self.location = None

    def _find_matches(self, srch, cont = None):
        if cont == None: cont = self.location.contains

        opts = {}
        for key, count in cont.items():
            c = self.getcls(key)
            if c.name.lower().startswith(srch.lower()):
                opts[key] = c

        return opts

    def export_state(self, name = "save"):
        output = {}
        output["state"] = {
            "player": self.player.xyname(),
            "location": self.location.xyname()
        }

        for k, v in self.tree.items():
            if not output.get(k): output[k] = {}

            for objname, val in v.items():
                output[k][objname] = val.xydata()

        print(output)
        save_to = story_path+"/saves/"+self.story.story().get('save_id', 'xyzzy')+"_"+name
        with open(save_to, "w+") as f:
            json.dump(output, f, indent=4)
            print("Saved to ", save_to)

    def log(self, text, sender = "world"):
        print(f" [{sender}] {text}")

    def init_story(self, name, save_name = None):
        try:
            self.tree = {"zones": {}, "objects": {}}
            self.player = None
            self.location = None
            self.story = importlib.import_module(name, package=None)
        except Exception as e:
            print(e)
            return False


        if save_name:
            print("Loading data", save_name)
            loadf = story_path+"/saves/"+self.story.story().get('save_id', 'xyzzy')+"_"+save_name
            with open(loadf, "r") as f:
                d = json.load(f)
                for objectName, props in d['objects'].items():
                    self.makecls(objectName, props)

                for objectName, props in d['zones'].items():
                    self.makecls(objectName, props)

                self.player = self.getcls(d['state']['player'])
                self.location = self.getcls(d['state']['location'])
        else:
            self.player = self.getcls(self.story.story()['player'])
            self.location = self.getcls(self.story.story()['start'])

        return True

    def isof(self, cls, sup):
        return issubclass(cls.__class__, sup)

    def makecls(self, name, make_with):
        """An aesthetic alias for getcls for when you just need to make the object and not use it"""
        return self.getcls(name, make_with)

    def getcls(self, name, make_with = None):
        if name in self.tree['objects'].keys():
            return self.tree['objects'][name]

        if name in self.tree['zones'].keys():
            return self.tree['zones'][name]

        try:
            new_cls = self.story.__dict__[name](self)
        except Exception as e:
            print(e)
            return None

        if make_with:
            new_cls.loadxyd(make_with)

        return new_cls


if __name__ == "__main__":
    sh = XySh()
    state = XyState()
    sh.set_xy(state)
    if len(sys.argv) == 2:
        sh.do_start(sys.argv[1])
    if len(sys.argv) == 3:
        sh.do_start(f"{sys.argv[1]} {sys.argv[2]}")
    sh.cmdloop()
    #state.init_story(name)
