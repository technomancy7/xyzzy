# System imports
import os, sys, shlex, json, textwrap

# Define script current location
HERE = os.path.dirname(__file__)+"/"

# Define custom library directory
sys.path.append(HERE+"lib/")

# UI libraries
from prompt_toolkit import prompt, PromptSession, print_formatted_text, HTML
from prompt_toolkit.completion import WordCompleter, NestedCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.shortcuts import yes_no_dialog, input_dialog, radiolist_dialog, message_dialog, clear
from prompt_toolkit.key_binding import KeyBindings
from dotenv import load_dotenv, set_key, dotenv_values
from ascii_canvas import canvas
from ascii_canvas import item
import importlib


"""
TODO
wrap the runtime in an error handler

"""
# Main state class
class Xyzzy:
    # Utils
    def boolinate(self, v):
        if type(v) == str:
            v = v.lower()

        if v in ["yes", "y", "true", "t", 1, "1", "on"]:
            return True

        if v in ["no", "n", "false", "f", 0, "0", "off"]:
            return False

        return False

    def _directions(self):
        'List of valid directions that zones can connect to'
        return ["north", "east", "south", "west", "up", "down", "in", "out"]

    def _reverse_direction(self, direction):
        'Reverses direction, up is down, east is west'
        match direction:
            case "up":
                return "down"
            case "down":
                return "up"
            case "in":
                return "out"
            case "out":
                return "in"
            case "north":
                return "south"
            case "south":
                return "north"
            case "east":
                return "west"
            case "west":
                return "east"

    # GUI
    def post_dialog(self, *, text = "", title = "Alert"):
        message_dialog(title=title, text=text).run()

    def get_confirm(self, *, text="Are you sure?", title="Confirmation"):
        return yes_no_dialog(title=title, text=text).run()

    def get_input(self, *, text="Enter your response:", title="Input"):
        return input_dialog(title=title, text=text).run()

    def get_choice(self, *, text="Select one option:", title="Choice", values=[]):
        return radiolist_dialog(title=title, text=text, values=values).run()

    def bottom_toolbar(self):
        l = self.location()
        n = l.get("name", "Undefined")
        d = l.get("description", "Undefined")
        return HTML(f'<b><style bg="ansired">{n}</style></b>  {d}')

    # Object creation
    def _create_actor(self, **opt):
        'Creates a raw new actor object.'
        actor = {
            "name": "",
            "id": "",
            "description": "",
            "health": 100,
            "energy": 100,
            "contains": [],
            "tags": [],
            "location": "",
            "events": {},
            "type": "actor"
        }
        actor.update(**opt)
        return actor

    def _create_zone(self, **opt):
        'Creates a raw new zone object.'
        zone = {
            "name": "",
            "id": "",
            "description": "",
            "contains": [],
            "tags": [],
            "type": "zone",
            "events": {},
            "exits": {}
        }

        # Fill the zone exits with the defined directions
        for d in self._directions():
            zone["exits"][d] = {"target": "", "lock": ""}

        zone.update(**opt)
        return zone


    def make_actor(self, actor_id, **opts):
        'Creates a new actor and adds it to the registry'
        opts["id"] = actor_id
        new_actor = self._create_actor(**opts)
        self.registry[actor_id] = new_actor

    def make_zone(self, zone_id, **opts):
        'Creates a new zone and adds it to the registry'
        opts["id"] = zone_id
        new_actor = self._create_zone(**opts)
        self.registry[zone_id] = new_actor


    # State management
    def reset_state(self):
        self.story_title = ""
        self.story_description = ""
        self.story_id = ""
        self.author = ""
        self.story_version = ""

        self.features = []
        self.maps = {}
        self.events = {}
        self.player_save_data = { # container for any information that may be kept in a players save file
            "goals": {},
            "notebook": []
        }
        self.registry = {} #All objects in the current state (actors and zones)
        self.vars = {} #Flags, switches, etc. Variables of the current state.
        self.focus = "" #The ID of the actor we're currently focused on, i.e. the Player
        self.scene = None
        self.admin = False #If we're in editor mode or not

    def load_state(self, sid = "", *, destructive = False):
        if self.story_id == "": return self.writeln("Load failed, story requires ID.")

        if sid == "":
            sid = "0"
        sv_name = f"save_{self.story_id}_{sid}.json"
        save_file = self.story_dir+"saves/"+sv_name
        if not os.path.exists(save_file):
            #print()
            return self.writeln(f"Load failed, file not found. ({save_file})")

        with open(save_file, "r") as f:
            js = json.load(f)
            if js["story_id"] == self.story_id:
                # If Destructive, completely overwrite the existing state with the prior state
                # Usually this is fine, but if a story template was changed, a non-destructive load is better
                # This inserts the prior state while generally preserving any changes in the template
                # For example: if a template adds new objects, a destructive load would erase the new objects
                #              while a non-destructive load would merely add the individual keys of the prior state
                #              and will not touch any new keys

                self.focus = js['focus']
                self.player_save_data = js['player_save_data']
                self.maps = js['maps']

                if destructive:
                    self.registry = js['registry']
                    self.vars = js['vars']

                else:
                    for k, v in js['registry'].items():
                        self.registry[k] = v

                    for k, v in js['vars'].items():
                        self.vars[k] = v

                self.writeln(f"State loaded from {sv_name}")
            else:
                self.writeln(f"Story ID mismatch. {js['story_id']} vs {self.story_id}")

    def save_state(self, sid = ""):
        if self.story_id == "": return self.writeln("Save failed, story requires ID.")

        if sid == "":
            sid = "0"

        sv_name = f"save_{self.story_id}_{sid}.json"

        with open(self.story_dir+"saves/"+sv_name, "w+") as f:
            js = {
                "story_id": self.story_id,
                "registry": self.registry,
                "vars": self.vars,
                "focus": self.focus,
                "player_save_data": self.player_save_data,
                "maps": self.maps
            }
            json.dump(js, f, indent=4)
            self.writeln(f"State saved to {sv_name}")


    def import_story(self, js):
        self.reset_state()
        self.story_title = js.get("title", "Undefined")
        self.story_description = js.get("description", "Undefined")
        self.story_id = js.get("id", "Undefined")
        self.author = js.get("author", "Undefined")
        self.story_version = js.get("version", "Undefined")
        self.protected = js.get("protected", False)
        self.events = js.get("events", {})
        self.registry = js.get("registry", {})
        self.vars = js.get("vars", {})
        self.focus = js.get("focus", "")
        self.maps = js.get("maps", "")
        self.features = js.get("features", [])

        self.scenes = {}
        
        for feature in self.features:
            mod = importlib.import_module(f"extensions.{feature}")

            try:
                for scene in mod.XYZZY['scenes']:
                    self.scenes[scene.__name__] = scene
                self.writeln(f"Loading extension: {mod.__name__}")
            except:
                pass

        if self.protected and self.admin:
            self.writeln("Edit mode is disabled for this story.")
            self.admin = False

    def clear_scene(self):
        if self.scene != None and hasattr(self.scene, "__exit_scene__"):
            self.scene.__exit_scene__()
        self.scene = None

    def set_scene(self, name):
        if self.scene != None and hasattr(self.scene, "__exit_scene__"):
            self.scene.__exit_scene__()

        if self.scenes.get(name):
            self.scene = self.scenes[name](self)
            if hasattr(self.scene, "__enter_scene__"):
                self.scene.__enter_scene__()


    def load_story(self, path):
        if not path.endswith(".json"):
            path = path+".json"

        if "\\" not in path and "/" not in path:
            path = self.story_dir+path

        if not os.path.exists(os.path.expanduser(path)):
            return self.writeln("Import failed, file not found.")

        with open(os.path.expanduser(path), "r") as f:
            self.import_story(json.load(f))
            self.writeln(f"Story imported: {path}")


    def export_story(self):
        # builds the json data of the story, used for editors to save an initial story state
        exported = {
            "title": self.story_title,
            "description": self.story_description,
            "author": self.author,
            "version": self.story_version,
            "focus": self.focus,
            "template": True,
            "id": self.story_id,
            "protected": self.protected,
            "maps": self.maps,

            "features": self.features,
            "events": self.events,
            "vars": self.vars,
            "registry": self.registry
        }

        return exported

    def save_story(self, path):
        if self.story_id == "": return self.writeln("Export failed, story requires ID.")

        if not path.endswith(".json"):
            path = path+".json"

        if "\\" not in path and "/" not in path:
            path = self.story_dir+path

        d = self.export_story()
        with open(os.path.expanduser(path), "w+") as f:
            json.dump(d, f, indent=4)
            self.writeln(f"Story exported: {path}")


    # Notes and Goals
    def add_note(self, text):
        if text not in self.player_save_data['notebook']:
            self.player_save_data['notebook'].append(text)
            self.writeln(text, source="Noted")

    def add_goal(self, goal_id, **opts):
        self.player_save_data["goals"][goal_id] = {
            "text": "",
            "state": 0, # -2 = failed, -1 = not shown, 0 = in-progress, 1 = complete
            "state_change": None, # either event name string, or callable object taking goal and state params
        }
        self.player_save_data["goals"][goal_id].update(**opts)

    def set_goal_state(self, goal_id, new_state:int):
        if self.player_save_data["goals"].get(goal_id):
            self.player_save_data["goals"][goal_id]['state'] = int(new_state)
            if self.player_save_data["goals"][goal_id].get("state_change"):
                if callable(self.player_save_data["goals"][goal_id]["state_change"]):
                    self.player_save_data["goals"][goal_id]["state_change"](goal = goal_id, state = new_state)

                if type(self.player_save_data["goals"][goal_id]["state_change"]) == str:
                    self.trigger_global_event(self.player_save_data["goals"][goal_id]["state_change"], goal = goal_id, state = new_state)

    # Core
    def __init__(self, *, load_cli = True):
        # System
        self.home_dir = HERE
        self.redirect = None # If not None, send input to this function

        self.story_dir = os.path.expanduser("~")+"/.xyzzy/"

        if not os.path.exists(self.story_dir):
            os.mkdir(self.story_dir)

        if not os.path.exists(self.story_dir+"saves/"):
            os.mkdir(self.story_dir+"saves/")

        if not os.path.exists(self.story_dir+".env"):
            with open(self.story_dir+".env", "w+") as f:
                f.write(textwrap.dedent("""\
                # Set true to disable auto-complete. (Default: false)
                XYZZY_DISABLE_AC='false'

                # Set true to disable terminal status bar. (Default: false)
                XYZZY_DISABLE_STATUSBAR='false'

                # Set true to disable terminal clearing every turn. (Default: false)
                XYZZY_DISABLE_CLS='false'
                """))

        load_dotenv(dotenv_path=self.story_dir+".env")

        if not os.path.exists(self.story_dir+".aliases"):
            with open(self.story_dir+".aliases", "w+") as f:
                f.write(textwrap.dedent("""\
                    # Atomic aliases, if the value starts with '!', if the entire line is the key, the line becomes the value
                    north='!move north'
                    n='!move north'

                    east='!move east'
                    e='!move east'

                    south='!move south'
                    s='!move south'

                    west='!move west'
                    w='!move west'

                    in='!move in'
                    i='!move in'

                    out='!move out'
                    o='!move out'

                    up='!move up'
                    u='!move up'

                    down='!move down'
                    d='!move down'

                    inv='!inventory'

                    sv='!save'
                    ld='!load'

                    # Partial aliases, if any word in the line is the key, that word becomes the value
                    nrth='north'
                    sth='south'
                    wst='west'
                    dwn='down'
                """))



        self.config = {
            "disable_autocomplete": self.boolinate(os.environ.get("XYZZY_DISABLE_AC", "false")),
            "disable_statusbar": self.boolinate(os.environ.get("XYZZY_DISABLE_STATUSBAR", "false")),
            "disable_cls": self.boolinate(os.environ.get("XYZZY_DISABLE_CLS", "false")),
        }

        # State
        self.protected = False #TODO implement compiled stories that can't be manually edited
        self.reset_state()

        if not os.path.exists(self.story_dir+"extensions/"):
            os.mkdir(self.story_dir+"extensions/")

        sys.path.append(self.story_dir)

        self.scenes = {}
        self.scene = None
        """for file in os.listdir(self.home_dir+"extensions/"):
            filename = os.fsdecode(file)
            if filename.endswith(".py"):
                print("home "+filename)

        for file in os.listdir(self.story_dir+"extensions/"):
            filename = os.fsdecode(file)
            if filename.endswith(".py"):
                print("story "+filename)"""


        # Var to check if we're in the core CLI or not, used for interfaces to check features
        self.cli = load_cli

        self.aliases = dotenv_values(self.story_dir+".aliases")
        self.prompt = "(> "
        self.running = False

        # CLI
        if load_cli:
            self.autocomplete = NestedCompleter.from_nested_dict({})
            bindings = KeyBindings()

            @bindings.add('c-t')
            def _(event):
                " TODO print info?"
                print(self.running, event)

            self.session = PromptSession(history=InMemoryHistory(), key_bindings=bindings)

    def build_map(self, label):
        "Returns a map canvas"
        #0 - left/right, 1 - up/down
        map = self.maps.get(label)
        if map:
            map_canvas = canvas.Canvas()
            for k, v in map.items():
                if k.startswith("_"):
                    map_canvas.add_item(item.Line(start=v[0], end=v[1]))
                else:
                    label = f"+{'-'*len(k)}+\n|{k}|\n+{'-'*len(k)}+"
                    map_canvas.add_item(item.Item(label, position=v))
            return map_canvas

    def read(self, text:str):
        'Main entry point for interfacing with the engine. Reads a string command.'

        if text in self.aliases.keys() and self.aliases[text].startswith("!"):
            text = self.aliases[text][1:]

        parts = text.split()
        for i, word in enumerate(parts):
            if word in self.aliases.keys() and not self.aliases[word].startswith("!"):
                parts[i] = self.aliases[word]

        text = " ".join(parts)
        self.writeln(f"{text}", source=self.focus_name(), colour="yellow", prefix = " * ", text_suffix="</grey>", text_prefix="<grey>")

        if len(text) == 0:
            return

        if self.scene != None and hasattr(self.scene, "read"):
            self.scene.read(text)
            return

        cmd = shlex.split(text)[0]
        line = ' '.join(shlex.split(text)[1:])

        #TODO have core commands and then overflow commands read from a table
        if self.admin:
            match cmd:
                case "help":
                    if line == "":
                        self.writeln("info play modify create delete move link export import")
                        self.writeln("set focus title author version description id")
                    else:
                        match line:
                            case "info":
                                self.writeln("Shows story info.", source=".info")

                            case "play":
                                self.writeln("Switches to player mode.", source=".play")

                            case "modify" | "mod" | "edit":
                                self.writeln("Modifies an objects properties.", source="modify")
                                self.writeln("Prompt-driven, takes no arguments.", source="modify")
                                self.writeln("Aliases: modify, mod, edit", source="modify")

                            case "create" | "cr" | "make":
                                self.writeln("Creates a new object", source="create")
                                self.writeln("Prompt-driven, takes no arguments.", source="create")
                                self.writeln("Aliases: create, cr, make", source="create")

                            case "delete" | "del" | "remove" | "rem" | "rm":
                                self.writeln("Deletes an object and all references to it.", source="delete")
                                self.writeln("Arguments: object_id", source="delete")
                                self.writeln("Aliases: delete, del, remove, rem, rm", source="delete")

                            case "move":
                                self.writeln("Moves an object in to a container.", source="move")
                                self.writeln("Arguments: object_id, target_zone_id", source="move")

                            case "link":
                                self.writeln("Connects one zone to another.", source="link")
                                self.writeln("Arguments: source_zone_id, direction, target_zone_id", source="link")

                            case "export":
                                self.writeln("Exports the story to a template file.", source="export")
                                self.writeln("Arguments: export_file_path", source="export")

                            case "import":
                                self.writeln("Imports a story template file.", source="export")
                                self.writeln("Arguments: story_file_path", source="export")

                            case "set":
                                self.writeln("Set a story variable.", source="set")
                                self.writeln("Arguments: set_format", source="set")
                                self.writeln(" - Format: key = value !optional_type", source="set")
                                self.writeln(" - Example: debug = true !bool", source="set")
                                self.writeln(" - !bool uses smart conversion, accepts:", source="set")
                                self.writeln("   - trues: yes, y, true, t, 1, on", source="set")
                                self.writeln("   - falses: no, n, false, f, 0, off", source="set")
                                self.writeln(" - !list splits values by commas.", source="set")
                                self.writeln("   - value 1, value 2, value 3", source="set")

                            case "focus":
                                self.writeln("Defines which actor is the story focus.", source="focus")
                                self.writeln("Arguments: actor_id", source="focus")

                            case "author" | "description" | "id" | "title" | "version":
                                self.writeln("Updates story metadata", source=line)
                                self.writeln("Arguments: new_value", source=line)

                case ".scene":
                    if line == "":
                        self.clear_scene()
                    else:
                        self.set_scene(line)

                case "info":
                    self.writeln(f"Story: {self.story_title or "Undefined"} ({self.story_id}{self.story_version or "Undefined"})")
                    self.writeln(f"<i>{self.story_description or "Undefined"}</i>")
                    self.writeln(f"By {self.author or "Undefined"}")

                    self.writeln(f"Focus: {self.focus or "Undefined"}")

                case "play" | "p":
                    self.writeln("Switched to Player mode.")
                    self.admin = False

                case "goals":
                    for k, goal in self.player_save_data['goals'].items():
                        self.writeln(goal)

                case "setgoal":
                    goal_id = line.split(" ")[0]
                    new_state = int(line.split(" ")[1])
                    self.set_goal_state(goal_id, new_state)


                case "goal":
                    gid = self.get_input(text = "Define goal unique ID")
                    gtext = self.get_input(text = "Define goal text")
                    gis = self.get_choice(text = "Define goal initial state", values = [("-2", "-2"), ("-1", "-1"), ("0", "0"), ("1", "1")])
                    gsc = self.get_input(text = "Define goal state change event")
                    self.writeln(f"Goal Added: {gid} -> {gtext} ({gis}) -> {gsc}")
                    self.add_goal(gid, text = gtext, state = int(gis), state_change = gsc)

                case "events":
                    self.writeln(" = Event Register = ")
                    for k, v in self.events.items():
                        self.writeln(f"{k} -> {v}")
                    self.writeln("")
                    self.writeln(" = Object Events =")
                    for _, obj in self.registry.items():
                        for k, v in obj.get("events", {}).items():
                            self.writeln(f"{obj['id']} -> {k} -> {v}")

                case "modify" | "mod" | "edit":
                    editor = ""

                    if line == "":
                        vals = []
                        for _, object in self.registry.items():
                            vals.append((object['id'], f"{object['name']} {object['id']}"))

                        editor = self.get_choice(values=vals)
                    else:
                        editor = line
                    while True:
                        key = self.get_input(text = f"Edit {self.registry[editor]['type']} {editor} key: (empty to end)")

                        if key in ["id", "events"]:
                            self.post_dialog(text = "key can not be modified.")
                            continue

                        if key == "" or key == None:
                            break

                        val = self.get_input(text = f"Set {key} value:")
                        #t = self.get_input(text = f"Set {key}={val} type: (str by default, int, float, list)")
                        t = self.get_choice(values=[("str", "str"), ("int", "int"), ("float", "float"), ("list", "list")])
                        if t == "int": val = int(val)
                        if t == "bool": val = self.boolinate(val)
                        if t == "float": val = float(val)
                        if t == "list":
                            val = val.split(",")
                            val = [item.strip() for item in val]

                        self.registry[editor][key] = val

                case "create" | "cr" | "make": #create a new object
                    new_type = self.get_choice(values=[("actor", "Actor"), ("zone", "Zone")])

                    new_id = self.get_input(text = f"Define new {new_type} UNIQUE ID:")
                    if new_id == "" or new_id == None:
                        return self.writeln("Creation aborted.")

                    if new_type == "actor":
                        self.make_actor(new_id)

                    elif new_type == "zone":
                        self.make_zone(new_id)

                    while True:
                        key = self.get_input(text = f"Edit {new_type} {new_id} key: (empty to end)")

                        if key in ["id", "events"]:
                            self.post_dialog(text = "key can not be modified.")
                            continue

                        if key == "" or key == None:
                            break

                        val = self.get_input(text = f"Set {key} value:")
                        #t = self.get_input(text = f"Set {key}={val} type: (str by default, int, float, list)")
                        t = self.get_choice(values=[("str", "str"), ("int", "int"), ("float", "float"), ("list", "list")])
                        if t == "int": val = int(val)
                        if t == "bool": val = self.boolinate(val)
                        if t == "float": val = float(val)
                        if t == "list":
                            val = val.split(",")
                            val = [item.strip() for item in val]

                        self.registry[new_id][key] = val

                    #print(self.registry)

                case "delete" | "del" | "remove" | "rem" | "rm":
                    #destroy an object completely and all references "delete <id>"
                    if self.registry.get(line):
                        for _, obj in self.registry.items():
                            #print(obj)
                            if line in obj['contains']:
                                obj['contains'].remove(line)
                                self.writeln(f"Removed object from location: {obj['id']}")

                        del self.registry[line]
                        self.writeln(f"Deleted {line}")

                case "move": #move an object to a zone "move <actor_id> <object_id>"
                    act_id = line.split(" ")[0]
                    targ_id = line.split(" ")[1]
                    self.writeln(f"Moving {act_id} in to {targ_id}.")
                    self.move_actor(act_id, targ_id)

                case "link": #connects two zones "link <zone_1_id> <direction> <zone_2_id>"
                    fz = line.split(" ")[0]
                    dr = line.split(" ")[1]
                    tz = line.split(" ")[2]

                    if dr in self._directions():
                        #self.writeln(f"SANITY CHECK: Attempting unlink {fz} via {dr}")
                        #self.unlink_zones(fz, dr) #sanity check, make sure old references don't exist before writing new routes
                        self.writeln(f"Connecting {fz} to {tz} via {dr} route.")
                        self.link_zones(fz, dr, tz)
                    else:
                        self.writeln("Direction invalid.", source="error")

                case "unlink": #connects two zones "link <zone_1_id> <direction> <zone_2_id>"
                    fz = line.split(" ")[0]
                    dr = line.split(" ")[1]

                    if dr in self._directions():
                        self.writeln(f"Disconnecting {fz} {dr} route.")
                        self.unlink_zones(fz, dr)
                    else:
                        self.writeln("Direction invalid.", source="error")

                case "export": #saves story file "export <file_path>"
                    if self.story_id == "": return self.writeln("Missing ID.")
                    self.save_story(self.story_id)

                case "import": #imports story file to state "import <file_path>"
                    if line == "":
                        choices = []
                        for file in os.listdir(self.story_dir):
                            filename = os.fsdecode(file)
                            if filename.endswith(".json"):
                                choices.append((filename, filename))


                        line = self.get_choice(values=choices)
                    self.load_story(line)

                case "eval":
                    self.writeln("Enter code: (Alt-Enter to send)")
                    code = prompt('> ', multiline=True)
                    self._eval_code(code)

                case "get":
                    if line != "":
                        self.writeln(f"{line} = {self.vars.get(line, 'Undefined')}")
                    else:
                        for k, v in self.vars.items():
                            self.writeln(f"{k} = {v}")

                case "set": #sets a flag "set <key>=<value> [!<type>]"
                    key = line.split("=")[0].strip()
                    val = "=".join(line.split("=")[1:]).split(" ")
                    if val[-1].startswith("!"):
                        t = val[-1]
                        val = " ".join(val[:-1]).strip()
                        if t == "!int": val = int(val)
                        if t == "!bool": val = self.boolinate(val)
                        if t == "!float": val = float(val)
                        if t == "!list":
                            val = val.split(",")
                            val = [item.strip() for item in val]
                    else:
                        val = " ".join(val).strip()
                    self.writeln(f"Setting {key} to {val} ({type(val).__name__})")
                    self.set_var(key, val)

                case "inspect":
                    if line != "":
                        obj = self.get_object(line)
                        if obj:
                            self.writeln(f"Output for {line}:")
                            for k, v in obj.items():
                                self.writeln(str(v), source=k)
                    else:
                        self.writeln(f" = Actors =")
                        for _, obj in self.registry.items():
                            if obj['type'] == 'actor':
                                self.writeln(f"{obj['id']} -> {obj['location'] or "<i>Undefined</i>"}")

                        self.writeln(f"")
                        self.writeln(f" = Zones =")
                        for _, obj in self.registry.items():
                            if obj['type'] == 'zone':
                                self.writeln(f"{obj['id']}")
                                for di, ex in obj['exits'].items():
                                    if ex['target']:
                                        self.writeln(f" -> {di} -> {ex['target']} ({ex['lock']})")
                case "focus":
                    if line == "":
                        return self.writeln(self.focus)
                    self.focus = line
                    self.writeln("Focus changed.")

                case "author":
                    if line == "":
                        return self.writeln(self.focus)
                    self.author = line
                    self.writeln("Author updated.")

                case "version":
                    if line == "":
                        return self.writeln(self.story_version)
                    self.story_version = line
                    self.writeln("Version updated.")

                case "title":
                    if line == "":
                        return self.writeln(self.story_title)
                    self.story_title = line
                    self.writeln("Title updated.")

                case "id":
                    if line == "":
                        return self.writeln(self.story_id)
                    self.story_id = line
                    self.writeln("ID updated.")

                case "description":
                    if line == "":
                        return self.writeln(self.story_description)
                    self.story_description = line
                    self.writeln("Description updated.")
        else:
            # Player Mode
            match cmd:
                case ".env":
                    k = self.get_input(text="Set Environ key:")
                    v = self.get_input(text="Set Environ value:")
                    set_key(self.story_dir+".env", k, v)

                case ".reset":
                    if self.get_confirm():
                        self.writeln("State reset.")
                        self.reset_state()

                case "map":
                    cvs = self.build_map(line)
                    if cvs:
                        self.writeln(f"\n{cvs.render()}", source="Map")
                    else:
                        self.writeln("Map not found.")

                case "alert":
                    self.post_dialog(text=line)

                case "import": #imports story file to state "import <file_path>"
                    if line == "":
                        choices = []
                        for file in os.listdir(self.story_dir):
                            filename = os.fsdecode(file)
                            if filename.endswith(".json"):
                                choices.append((filename, filename))


                        line = self.get_choice(values=choices)

                    self.load_story(line)

                case "save":
                    self.writeln("Saving...")
                    self.save_state(line)

                case "load":
                    self.writeln("Loading...")
                    self.load_state(line)

                case "edit" | "admin":
                    if self.protected:
                        return self.writeln("Edit mode is disabled for this story.")
                    self.writeln("Switched to Admin mode.")
                    self.admin = True

                case "goals":
                    for k, goal in self.player_save_data['goals'].items():
                        if goal['state'] == 1:
                            self.writeln(goal['text'], source="Goal")

                        if line == "!" and goal['state'] == 2:
                            self.writeln(f"<s>{goal['text']}</s>", source="Goal")


                case "note":
                    self.add_note(line)

                case "notes" | "notebook":
                    for note in self.player_save_data['notebook']:
                        self.writeln(note, source="Note")

                case "unnote":
                    if len(self.player_save_data['notebook']) == 0: return self.writeln("No notes to remove.")

                    choices = []
                    for i, note in enumerate(self.player_save_data['notebook']):
                        choices.append((i, note))

                    to_remove = self.get_choice(values=choices)
                    self.writeln(f"Removed note: {self.player_save_data['notebook'][to_remove]}.")
                    self.player_save_data['notebook'].remove(self.player_save_data['notebook'][to_remove])

                case "move": #move player in set direction "move <direction>"
                    if line in self._directions():
                        loc = self.location()
                        e = loc['exits'][line]
                        if e['target']:
                            if e['lock']:
                                return self.writeln(f"You can't go that way. {e['lock']}")

                            self.writeln(f"Moving to {e['target']}.")

                case "inventory":
                    player = self.get_object(self.focus)
                    if line == "full":
                        for item in player['contains']:
                            obj = self.get_object(item)
                            self.writeln(f"{obj['name']} - {obj['description']}")
                            self.writeln(f"Tags: {obj['tags']}")
                            self.writeln("")
                    else:
                        self.writeln(", ".join([self.get_object(item)['name'] for item in player['contains']]))

                case "look":
                    # TODO make a version in admin mode which shows the ID's
                    l = self.location()
                    self.writeln(f"You are in {l['name']}.")
                    if l['description']:
                        self.writeln(f"<i>{l['description']}</i>")

                    for d, exit in l['exits'].items():
                        if exit['target']:
                            self.writeln(f"You can see {self.get_name(exit['target'], False)} to the {d}.")
                    items = []
                    for i in l['contains']:
                        if i != self.focus:
                            items.append(i)

                    if len(items) > 0:

                        item_names = [self.get_name(item) for item in items]
                        self.writeln(f"You can see {', '.join(item_names)}")
                        #self.writeln()

                case "take": #picks up object if object can be taken "take <object name>"
                    loc = self.location()
                    for i in loc['contains']:
                        obj = self.get_object(i)
                        name = obj['name']
                        #print(obj)
                        if line.lower() == name.lower() and "inventory" in obj['tags']:
                            self.move_actor(i, self.focus)
                            self.writeln(obj['name'], source="Take")
                            self.trigger_object_event(obj['id'], "taken", target = obj['id'], instigator = self.focus)

                case "drop": #drops item from ivnentory in to current zone if not restricted "drop <name>"
                    loc = self.get_object(self.focus)
                    for i in loc['contains']:
                        obj = self.get_object(i)
                        name = obj['name']
                        if line.lower() == name.lower() and "inventory" in obj['tags']:
                            self.move_actor(i, loc['location'])
                            self.writeln(obj['name'], source="Drop")
                            self.trigger_object_event(obj['id'], "dropped", target = obj['id'], instigator = self.focus)

                case "equip" | "wear": #if item in inventory is equippable, set as equipped
                    loc = self.get_object(self.focus)
                    for i in loc['contains']:
                        obj = self.get_object(i)
                        name = obj['name']
                        if line.lower() == name.lower() and "equipment" in obj['tags'] and "equipped" not in obj["tags"]:
                            obj['tags'].append("equipped")
                            self.writeln(obj['name'], source="Equipped")
                            self.trigger_object_event(obj['id'], "equipped", target = obj['id'], instigator = self.focus)

                case "unequip" | "unwear": #if item is equipped, remove
                    loc = self.get_object(self.focus)
                    for i in loc['contains']:
                        obj = self.get_object(i)
                        name = obj['name']
                        if line.lower() == name.lower() and "equipment" in obj['tags'] and "equipped" in obj["tags"]:
                            if "locked" in obj['tags']:
                                return self.writeln(f"{obj['name']} can't be removed.")

                            obj['tags'].remove("equipped")
                            self.writeln(obj['name'], source="Unequipped")
                            self.trigger_object_event(obj['id'], "unequipped", target = obj['id'], instigator = self.focus)

                case "use": #if item in inventory is usable, use it
                    loc = self.get_object(self.focus)
                    for i in loc['contains']:
                        obj = self.get_object(i)
                        name = obj['name']
                        if line.lower() == name.lower():
                            self.writeln(obj['name'], source="Used")
                            self.trigger_object_event(obj['id'], "used", target = obj['id'], instigator = self.focus)

                case "talk" | "speak": #if actor in zone is talkable, talk
                    loc = self.location()
                    for i in loc['contains']:
                        obj = self.get_object(i)
                        name = obj['name']
                        #print(obj)
                        if line.lower() == name.lower():
                            self.writeln(obj['name'], source="Talk")
                            self.trigger_object_event(obj['id'], "talked", target = obj['id'], instigator = self.focus)

                case "hit" | "strike": #hits actor in zone, damage if damageable, activate event if exists
                    loc = self.location()
                    for i in loc['contains']:
                        obj = self.get_object(i)
                        name = obj['name']
                        #print(obj)
                        if line.lower() == name.lower():
                            self.writeln(obj['name'], source="Striked")
                            self.trigger_object_event(obj['id'], "hit", target = obj['id'], instigator = self.focus)

    def _eval_code(self, code, **opts):
        env = {
            "xyzzy": self,
            "eval": None,
            "exec": None,
            "builtins": None,
            "obj": self.get_object,
            "player": self.get_object(self.focus),
            "print": self.writeln
        }
        env.update(**opts)
        eval(code, env)

    def writeln(self, text, source = "Xyzzy", colour = "skyblue", text_prefix = "", text_suffix = "", prefix = ""):
        if len(prefix) > 3: prefix = prefix[:3]
        print_formatted_text(HTML(f'{prefix}{' '*(3-len(prefix))}<{colour}>[{source}]</{colour}>\t{text_prefix}{text}{text_suffix}'))

    def run(self):
        'Default command-line shell interface'
        self.running = True
        self.rebuild_autocomplete()
        if not self.config.get("disable_cls"): clear()

        # TODO story intro here

        while self.running:
            try:
                hud = None
                if not self.config.get("disable_statusbar"): hud = self.bottom_toolbar
                text = self.session.prompt(
                    self.prompt, completer=self.autocomplete, complete_while_typing=False,
                    auto_suggest=AutoSuggestFromHistory(),
                    bottom_toolbar=hud
                )
                if not self.config.get("disable_cls"): clear()
                self.read(text)
                self.rebuild_autocomplete()

            except KeyboardInterrupt:
                print("bye") # TODO save data here
                self.running = False

    def set_var(self, key, value):
        self.vars[key] = value

    def touch_var(self, key, default_var = None):
        return self.vars.get(key, default_var)

    def rebuild_autocomplete(self):
        # TODO
        loc = self.location()

        if self.admin:
            acd = {
                "link": {},
            }

            for k, v in self.registry.items():
                if v['type'] == "zone":
                    acd['link'][k] = {}
                    for d in self._directions():
                        acd['link'][k][d] = {}
                        for sk, sv in self.registry.items():
                            if sv['type'] == "zone":
                                acd['link'][k][d][sk] = None
        else:
            acd = {
                "move": {},
                "take": {},
                "drop": {},

                "inventory": None
            }

            for k, v in self.registry.items():
                if v['type'] == "actor" and v['location'] == loc['id'] and "inventory" in v['tags']:
                    acd['take'][v['name']] = None

                if v['type'] == "actor" and v['location'] == self.focus and "inventory" in v['tags']:
                    acd['drop'][v['name']] = None

            for d in self._directions():
                acd['move'][d] = None

        self.autocomplete = NestedCompleter.from_nested_dict(acd)

    def add_autocomplete(self, word:str):
        self.autocomplete.words.append(word)

    def set_autocomplete(self, ar:list):
        self.autocomplete.words = ar


    # Object management
    def move_actor(self, act_id, target_id):
        if self.registry.get(act_id) and self.registry.get(target_id) and self.registry[act_id]['type'] == "actor":
            for _, obj in self.registry.items():
                if act_id in obj['contains']:
                    obj['contains'].remove(act_id)
                    #print(f"Removed object from location: {obj['id']}")

                if obj['id'] == target_id:
                    obj['contains'].append(act_id)
                    #print(f"Added object to location: {obj['id']}")

            self.registry[act_id]['location'] = target_id
            #print(f"Updated location value: {self.registry[act_id]['location']}")

    def unlink_zones(self, first, direction):
        fz = self.get_object(first)
        if fz == None or fz['type'] != "zone":
            return self.writeln(f"Object {first} is not a valid zone.")

        other = self.get_object(fz['exits'][direction]['target'])
        if other:
            self.writeln(f"Severing connection between {first} and {other['id']} via {direction} route.")
            other['exits'][self._reverse_direction(direction)]['target'] = ""
            fz['exits'][direction]['target'] = ""


    def link_zones(self, first_zone, direction, target_zone):
        for _, zone in self.registry.items():
            if zone["type"] == "zone" and zone['id'] == first_zone:
                zone["exits"][direction]["target"] = target_zone

            if zone["type"] == "zone" and zone['id'] == target_zone:
                zone["exits"][self._reverse_direction(direction)]["target"] = first_zone

    def tagged(self, obj_id, tag):
        if self.registry.get(obj_id):
            return tag in self.registry[obj_id].get("tags", [])

    def tag(self, obj_id, new_tag):
        if self.registry.get(obj_id):
            if new_tag not in self.registry[obj_id].get("tags", []):
                self.registry[obj_id].get("tags", []).append(new_tag)

    def untag(self, obj, tag):
        if self.registry.get(obj_id):
            if new_tag in self.registry[obj_id].get("tags", []):
                self.registry[obj_id].get("tags", []).remove(new_tag)

    def get_name(self, obj_id, include_article = True):
        if include_article:
            obj = self.registry.get(obj_id, {})
            return obj.get("article", "a")+" "+obj.get("name", "")
        else:
            return self.registry.get(obj_id, {}).get("name", "")

    def trigger_global_event(self, name, **opts):
        print("Triggering", name, opts)
        for k, evt in self.events.items():
            if k == name:
                #code = evt.replace("{$}", obj_id)
                self._eval_code(evt, **opts)

    def trigger_object_event(self, obj_id, name, **opts):
        obj = self.get_object(obj_id)
        if obj.get("events"):
            evts = obj['events'].get(name, [])

            for evt in evts:
                if evt.startswith("g:"):
                    code = self.events.get(evt.split(":")[1])
                    code = code.replace("{$}", obj_id)
                    self._eval_code(code, **opts)
                else:
                    code = evt.replace("{$}", obj_id)
                    self._eval_code(evt, **opts)

    def get_object(self, id):
        return self.registry.get(id, None)

    def location(self, obj_id = ""):
        'returns location object of the target, focus by default'
        if obj_id == "": obj_id = self.focus
        #print("Getting loc of", obj_id)
        obj = self.get_object(obj_id)
        if obj:
            loc = self.get_object(obj['location'])

            if loc:
                return loc

        # If no location is found, return an empty default object, to try and prevent errors
        return self._create_zone()

    def set_focus(self, name):
        self.focus = name # TODO add validation

    def focus_name(self): # TODO
        'Returns the Name of the current focus'

        foc = self.get_object(self.focus)
        if foc: return foc['name']
        return "Player"
