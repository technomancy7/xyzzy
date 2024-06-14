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
from prompt_toolkit.shortcuts import yes_no_dialog, input_dialog, radiolist_dialog
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
            "type": "zone",
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
        self.author = ""
        self.story_version = ""

        self.registry = {} #All objects in the current state (actors and zones)
        self.data = {} #Flags, switches, etc. Variables of the current state.
        self.focus = "" #The ID of the actor we're currently focused on, i.e. the Player

        self.admin = False #If we're in editor mode or not

    def __init__(self, *, load_cli = True):
        # System
        self.home_dir = HERE
        self.redirect = None # If not None, send input to this function

        # State
        self.reset_state()

        # Var to check if we're in the core CLI or not, used for interfaces to check features
        self.cli = load_cli

        # CLI
        if load_cli:
            #self.console = Console()
            self.autocomplete = WordCompleter([], ignore_case=True)
            #self.set_autocomplete(["look","shout", "shove"])
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



    def read(self, text:str):
        'Main entry point for interfacing with the engine. Reads a string command.'
        self.writeln(f"{text}", source=self.focus_name())

        if len(text) == 0:
            return

        if self.redirect != None:
            self.redirect(text)
            return

        cmd = shlex.split(text)[0]
        line = ' '.join(shlex.split(text)[1:])

        if self.admin: #TODO have core commands and then overflow commands read from a table
            # Editor Mode
            match cmd:
                case ".info":
                    self.writeln(f"Story: {self.story_title or "Undefined"} ({self.story_version or "Undefined"})")
                    self.writeln(f"<i>{self.story_description or "Undefined"}</i>")
                    self.writeln(f"By {self.author or "Undefined"}")

                case ".play":
                    self.writeln("Switched to Player mode.")
                    self.admin = False

                case "create": #create a new object "create <type>, key=value, ..."
                    new_type = self.get_choice(values=[("actor", "Actor"), ("zone", "Zone")])

                    new_id = self.get_input(text = f"Define new {new_type} UNIQUE ID:")
                    if new_id == "" or new_id == None:
                        return self.writeln("Creation aborted.")
                    self.make_actor(new_id)

                    while True:
                        key = self.get_input(text = "Edit object key: (empty to end)")
                        if key == "" or key == None:
                            break

                        val = self.get_input(text = f"Set {key} value:")
                        t = self.get_input(text = f"Set {key}={val} type: (str by default, int, float, list)")
                        if t == "int": val = int(val)
                        if t == "float": val = float(val)
                        if t == "list": val = val.split(",")

                        self.registry[new_id][key] = val

                    print(self.registry)

                case "delete": #destroy an object completely and all references "delete <id>"
                    pass

                case "move": #move an object to a zone "move <actor_id> <object_id>"
                    pass

                case "link": #connects two zones "link <zone_1_id> <direction> <zone_2_id>"
                    pass

                case "export": #saves story file "export <file_path>"
                    pass

                case "import": #imports story file to state "import <file_path>"
                    pass

                case "set": #sets a flag "set <key>=<value> [!<type>]"
                    pass

                case "modify": #manually edits an objects values "modify <id> <key>=<value> [!<type>]"
                    pass

                case "focus":
                    self.focus = line
                    self.writeln("Focus changed.")

                case "author":
                    self.author = line
                    self.writeln("Author updated.")

                case "version":
                    self.story_version = line
                    self.writeln("Version updated.")

                case "title":
                    self.story_title = line
                    self.writeln("Title updated.")

                case "description":
                    self.story_description = line
                    self.writeln("Description updated.")
        else:
            # Player Mode
            match cmd:
                case ".reset":
                    if self.get_confirm():
                        self.writeln("State reset.")
                        self.reset_state()

                case ".save" | ".s":
                    pass

                case ".load" | ".l":
                    pass

                case ".edit" | ".admin":
                    self.writeln("Switched to Admin mode.")
                    self.admin = True

                case "move": #move player in set direction "move <direction>"
                    #alias shortcuts populated from directions as overflow custom commands, n, north etc
                    pass

                case "look": #show current zone information
                    pass

                case "take": #picks up object if object can be taken "take <object name>"
                    pass

                case "drop": #drops item from ivnentory in to current zone if not restricted "drop <name>"
                    pass

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



    def writeln(self, text, source = "Xyzzy", colour = "skyblue"):
        #self.console.print(f"1 [{colour}]{source}[/{colour}]: {text}")
        print_formatted_text(HTML(f'<{colour}>[{source}]</{colour}>: {text}'))

    def bottom_toolbar(self):
        l = self.location()
        n = l.get("location", "Undefined")
        d = l.get("description", "Undefined")
        return HTML(f'<b><style bg="ansired">{n}</style></b>  {d}')

    def run(self):
        'Default command-line shell interface'
        self.running = True
        self.add_autocomplete("borkerinorana")
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

    def location(self): # TODO
        'returns location object of the current focus/player'
        return {
            "name": "Undefined",
            "description": "Default location template"
        }

    def set_focus(self, name):
        self.focus = name # TODO add validation

    def focus_name(self): # TODO
        'Returns the Name of the current focus'
        return "Player"

    def set_var(self, key, value):
        self.data[key] = value

    def touch_var(self, key, default_var = None):
        return self.data.get(key, default_var)

    def add_autocomplete(self, word:str):
        self.autocomplete.words.append(word)

    def set_autocomplete(self, ar:list):
        self.autocomplete.words = ar
