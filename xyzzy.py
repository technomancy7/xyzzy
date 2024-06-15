# System imports
import os, sys, shlex, json, textwrap

# Define script current location
HERE = os.path.dirname(__file__)+"/"

# Define custom library directory
sys.path.append(HERE+"lib/")

# UI libraries
from prompt_toolkit import prompt, PromptSession, print_formatted_text, HTML
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.shortcuts import yes_no_dialog, input_dialog, radiolist_dialog, message_dialog
#from rich.console import Console
#from rich.panel import Panel
from prompt_toolkit.key_binding import KeyBindings

"""
concept for events

actor {
    "events": {
        "hit": ["hit_thing"]
    }
}

# story container for event macros
events {
    "hit_thing": "xyzzy.damage_object('{$}', 10);xyzzy.writeln('{$name} was damaged by {$inst}.')"
}

# idea
string is evaluated in py eval(), give access to the xyzzy state object as `xyzzy`
before eval: {$} is replaced with with id of target object, {$name} is replaced with name, {$inst} for instigator (i.e. player)
"""
# Main state class
class Xyzzy:
    def post_dialog(self, *, text = "", title = "Alert"):
        message_dialog(title=title, text=text).run()

    def get_confirm(self, *, text="Are you sure?", title="Confirmation"):
        return yes_no_dialog(title=title, text=text).run()

    def get_input(self, *, text="Enter your response:", title="Input"):
        return input_dialog(title=title, text=text).run()

    def get_choice(self, *, text="Select one option:", title="Choice", values=[]):
        return radiolist_dialog(
            title=title,
            text=text,
            values=values
        ).run()

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

    def reset_state(self):
        self.story_title = ""
        self.story_description = ""
        self.story_id = ""
        self.author = ""
        self.story_version = ""

        self.events = {}
        self.registry = {} #All objects in the current state (actors and zones)
        self.vars = {} #Flags, switches, etc. Variables of the current state.
        self.focus = "" #The ID of the actor we're currently focused on, i.e. the Player

        self.admin = False #If we're in editor mode or not

    def load_state(self, sid = ""):
        if sid == "":
            sid = "0"
        sv_name = f"save_{self.story_id}_{sid}.json"

        with open(self.story_dir+"saves/"+sv_name, "r") as f:
            js = json.load(f)
            if js["story_id"] == self.story_id:
                self.registry = js['registry']
                self.vars = js['vars']
                self.focus = js['focus']
                self.writeln(f"State loaded from {sv_name}")
            else:
                self.writeln("Story ID mismatch.")

    def save_state(self, sid = ""):
        if sid == "":
            sid = "0"
        sv_name = f"save_{self.story_id}_{sid}.json"

        with open(self.story_dir+"saves/"+sv_name, "w+") as f:
            js = {
                "story_id": self.story_id,
                "registry": self.registry,
                "vars": self.vars,
                "focus": self.focus
            }
            json.dump(js, f, indent=4)
            self.writeln(f"State saved to {sv_name}")

    def import_story(self, js):
        self.story_title = js.get("title", "Undefined")
        self.story_description = js.get("description", "Undefined")
        self.story_id = js.get("id", "Undefined")
        self.author = js.get("author", "Undefined")
        self.story_version = js.get("version", "Undefined")

        self.events = js.get("events", {})
        self.registry = js.get("registry", {})
        self.vars = js.get("vars", {})
        self.focus = js.get("focus", "")

    def load_story(self, path):
        if not path.endswith(".json"):
            path = path+".json"

        if "\\" not in path and "/" not in path:
            path = self.story_dir+path

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

            "events": self.events,
            "vars": self.vars,
            "registry": self.registry
        }

        return exported

    def save_story(self, path):
        if not path.endswith(".json"):
            path = path+".json"

        if "\\" not in path and "/" not in path:
            path = self.story_dir+path

        d = self.export_story()
        with open(os.path.expanduser(path), "w+") as f:
            json.dump(d, f, indent=4)
            self.writeln(f"Story exported: {path}")

    def __init__(self, *, load_cli = True):
        # System
        self.home_dir = HERE
        self.redirect = None # If not None, send input to this function

        self.story_dir = os.path.expanduser("~")+"/.xyzzy/"

        if not os.path.exists(self.story_dir):
            os.mkdir(self.story_dir)

        if not os.path.exists(self.story_dir+"saves/"):
            os.mkdir(self.story_dir+"saves/")

        # State
        self.reset_state()

        # Var to check if we're in the core CLI or not, used for interfaces to check features
        self.cli = load_cli

        # CLI
        if load_cli:
            self.autocomplete = WordCompleter([], ignore_case=True)
            bindings = KeyBindings()

            @bindings.add('c-t')
            def _(event):
                " TODO print info?"
                print(self.running, event)

            self.session = PromptSession(history=InMemoryHistory(), key_bindings=bindings)
            self.prompt = "(> "
            self.running = False
            self.show_hud = True
            self.clear_screen = False

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

    def link_zones(self, first_zone, direction, target_zone):
        for _, zone in self.registry.items():
            if zone["type"] == "zone" and zone['id'] == first_zone:
                zone["exits"][direction]["target"] = target_zone

            if zone["type"] == "zone" and zone['id'] == target_zone:
                zone["exits"][self._reverse_direction(direction)]["target"] = first_zone

    def read(self, text:str):
        'Main entry point for interfacing with the engine. Reads a string command.'
        self.writeln(f"{text}", source=self.focus_name(), colour="yellow", prefix = " * ", text_suffix="</grey>", text_prefix="<grey>")

        if len(text) == 0:
            return

        if self.redirect != None:
            self.redirect(text)
            return

        cmd = shlex.split(text)[0]
        line = ' '.join(shlex.split(text)[1:])

        #TODO have core commands and then overflow commands read from a table
        if self.admin:
            match cmd:
                case ".help":
                    if line == "":
                        self.writeln(".info .play modify create delete move link export import")
                        self.writeln("set focus title author version description id")
                    else:
                        match line:
                            case ".info":
                                self.writeln("Shows story info.", source=".info")

                            case ".play":
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
                case "info":
                    self.writeln(f"Story: {self.story_title or "Undefined"} ({self.story_id}{self.story_version or "Undefined"})")
                    self.writeln(f"<i>{self.story_description or "Undefined"}</i>")
                    self.writeln(f"By {self.author or "Undefined"}")

                    self.writeln(f"Focus: {self.focus or "Undefined"}")

                case ".play" | ".p" | ".":
                    self.writeln("Switched to Player mode.")
                    self.admin = False

                case "events":
                    self.writeln(self.events)
                case "modify" | "mod" | "edit":
                    vals = []
                    for _, object in self.registry.items():
                        vals.append((object['id'], object['name'] or object['id']))

                    editor = self.get_choice(values=vals)

                    while True:
                        key = self.get_input(text = f"Edit {self.registry[editor]['type']} {editor} key: (empty to end)")

                        if key == "id":
                            self.post_dialog(text = "ID can not be modified.")
                            continue

                        if key == "" or key == None:
                            break

                        val = self.get_input(text = f"Set {key} value:")
                        t = self.get_input(text = f"Set {key}={val} type: (str by default, int, float, list)")
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

                        if key == "id":
                            self.post_dialog(text = "ID can not be modified.")
                            continue

                        if key == "" or key == None:
                            break

                        val = self.get_input(text = f"Set {key} value:")
                        t = self.get_input(text = f"Set {key}={val} type: (str by default, int, float, list)")
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
                        self.writeln(f"Connecting {fz} to {tz} via {dr} route.")
                        self.link_zones(fz, dr, tz)
                    else:
                        self.writeln("Direction invalid.", source="error")

                case "export": #saves story file "export <file_path>"
                    if line == "" and self.story_id != "":
                        line = self.story_id

                    if line == "": return self.writeln("Missing ID.")
                    self.save_story(line)

                case "import": #imports story file to state "import <file_path>"
                    if line == "":
                        choices = []
                        for file in os.listdir(self.story_dir):
                            filename = os.fsdecode(file)
                            if filename.endswith(".json"):
                                choices.append((filename, filename))


                        line = self.get_choice(values=choices)
                    self.load_story(line)

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
                case ".alert":
                    self.post_dialog(text=line)

                case ".reset":
                    if self.get_confirm():
                        self.writeln("State reset.")
                        self.reset_state()

                case ".save" | ".s":
                    self.writeln("Saving.")
                    self.save_state(line)

                case ".load" | ".l":
                    self.writeln("Loading.")
                    self.load_state(line)

                case ".edit" | ".admin":
                    self.writeln("Switched to Admin mode.")
                    self.admin = True

                case "move": #move player in set direction "move <direction>"
                    #alias shortcuts populated from directions as overflow custom commands, n, north etc
                    pass

                case "inventory":
                    player = self.get_object(self.focus)
                    print(player['contains'])
                case "look":
                    l = self.location()
                    self.writeln(f"You are in {l['name']}.")
                    if l['description']:
                        self.writeln(f"<i>{l['description']}</i>")

                    items = []
                    for i in l['contains']:
                        if i != self.focus:
                            items.append(i)

                    if len(items) > 0:
                        self.writeln("You can see:")
                        item_names = [self.get_object(item)['name'] for item in items]
                        self.writeln(", ".join(item_names))

                case "take": #picks up object if object can be taken "take <object name>"
                    loc = self.location()
                    for i in loc['contains']:
                        obj = self.get_object(i)
                        name = obj['name']
                        #print(obj)
                        if line.lower() == name.lower() and "inventory" in obj['tags']:
                            self.move_actor(i, self.focus)
                            self.writeln(obj['name'], source="Take")
                            self.trigger_event(obj['id'], "taken", target = obj['id'], instigator = self.focus)
                            return

                case "drop": #drops item from ivnentory in to current zone if not restricted "drop <name>"
                    loc = self.get_object(self.focus)
                    for i in loc['contains']:
                        obj = self.get_object(i)
                        name = obj['name']
                        if line.lower() == name.lower() and "inventory" in obj['tags']:
                            self.move_actor(i, loc['location'])
                            return self.writeln(obj['name'], source="Drop")

                case "equip" | "wear": #if item in inventory is equippable, set as equipped
                    pass

                case "unequip" | "unwear": #if item is equipped, remove
                    pass

                case "use": #if item in inventory is usable, use it
                    pass

                case "talk" | "speak": #if actor in zone is talkable, talk
                    pass

                case "hit" | "strike": #hits actor in zone, damage if damageable, activate event if exists
                    pass

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

    def trigger_event(self, obj_id, name, **opts):
        obj = self.get_object(obj_id)
        evts = obj['events'].get(name, [])

        for evt in evts:
            if evt.startswith("g:"):
                code = self.events.get(evt.split(":")[1])
                code = code.replace("{$}", obj_id)
                self._eval_code(code, **opts)
            else:
                code = evt.replace("{$}", obj_id)
                self._eval_code(evt, **opts)

    def boolinate(self, v):
        if type(v) == str:
            v = v.lower()

        if v in ["yes", "y", "true", "t", 1, "1", "on"]:
            return True

        if v in ["no", "n", "false", "f", 0, "0", "off"]:
            return False

        return False

    def writeln(self, text, source = "Xyzzy", colour = "skyblue", text_prefix = "", text_suffix = "", prefix = ""):
        if len(prefix) > 3: prefix = prefix[:3]
        print_formatted_text(HTML(f'{prefix}{' '*(3-len(prefix))}<{colour}>[{source}]</{colour}>\t{text_prefix}{text}{text_suffix}'))

    def bottom_toolbar(self):
        l = self.location()
        n = l.get("name", "Undefined")
        d = l.get("description", "Undefined")
        return HTML(f'<b><style bg="ansired">{n}</style></b>  {d}')

    def run(self):
        'Default command-line shell interface'
        self.running = True

        while self.running:
            try:
                hud = None
                if self.show_hud: hud = self.bottom_toolbar
                text = self.session.prompt(
                    self.prompt, completer=self.autocomplete, complete_while_typing=False,
                    auto_suggest=AutoSuggestFromHistory(),
                    bottom_toolbar=hud
                )
                if self.clear_screen: self.console.clear()
                self.read(text)

            except KeyboardInterrupt:
                print("bye") # TODO save data here
                self.running = False

    def get_object(self, id):
        return self.registry.get(id, None)

    def location(self, obj_id = ""):
        'returns location object of the target, focus by default'
        if obj_id == "": obj_id = self.focus
        loc = self.get_object(self.get_object(obj_id)['location'])

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

    def set_var(self, key, value):
        self.vars[key] = value

    def touch_var(self, key, default_var = None):
        return self.vars.get(key, default_var)

    def add_autocomplete(self, word:str):
        self.autocomplete.words.append(word)

    def set_autocomplete(self, ar:list):
        self.autocomplete.words = ar
