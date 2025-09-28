import sys, os, importlib, cmd, readline, json
from xyobjects import Human, InventoryItem
story_path = os.path.expanduser("~/.xyzzy-stories")
sys.path.append(story_path)

class XySh(cmd.Cmd):
    intro = 'Welcome to Xyzzy. Type LOAD followed by a story name to begin.\n'
    prompt = '(No story loaded) '

    def set_xy(self, state):
        self.state = state
        self.state.sh = self

    def do_shell(self, arg):
        if arg.startswith("!"):
            os.system(arg[1:])
        else:
            try:
                e = compile(arg, "<string>", "eval")
                g = {
                    "sh": self,
                    "state": self.state,
                    "player": self.state.player,
                    "location": self.state.location,
                    "log": self.state.log
                }
                eval(e, g)
            except Exception as e:
                print(e)


    def do_echo(self, arg):
        print("You said:", arg)

    def do_talk(self, target):
        pass
        # TODO check if target is in contains key of location like take, but check if it extends Human and has on_talk event

    def do_take(self, item_name):
        pass
        """
        TODO
        lool at Location, see if name is in contains, subtract the count by 1 (delete from table if 0), add to player inventory table by increment value + 1 (create key if dont have)

        sanity check, get the cls and check if it extends InventoryItem first

        """

    def do_drop(self, item_name):
        pass
        """
        TODO
        opposite of take

        """

    def do_look(self, arg):
        print(self.state.player.health)

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
        self.story = None
        self.sh = None

        self.player = None
        self.location = None

    def export_state(self, name = "save"):
        output = {}
        output["state"] = {
            "player": self.player.__class__.__name__,
            "location": self.location.__class__.__name__
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
                #self.player.loadxyd(d[])
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

        new_cls = self.story.__dict__[name](self)

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
