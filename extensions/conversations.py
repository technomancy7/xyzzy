import shlex

class Convo:
    def __init__(self, state):
        self.state = state

        self.convo_data = {}
        self.current_target = ""
        self.current_stage = "start"

    def __statusbar__(self):
        return f"Speaking with {self.convo_data.get('_speaker', '???')}"

    def handle_conditional(self, s):
        if s not in self.convo_data[self.current_stage].get("conditions", {}).keys():
            return True
        c = self.convo_data[self.current_stage].get("conditions", {})[s]
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

    def __next_stage__(self, stage_name):
        writeln = self.state.writeln

        if not self.convo_data.get(stage_name):
            return writeln(f"Story error: stage_name {stage_name} not found.")

        self.current_stage = stage_name
        self.state.rebuild_autocomplete()
        writeln(self.convo_data[stage_name].get("text", "..."), source = f"{self.convo_data.get('_speaker', '???')}")

        for i, choice in enumerate(self.convo_data[stage_name].get("options", {}).keys()):
            if self.handle_conditional(choice):
                writeln(choice, source = str(i), prefix = " ?")
            else:
                writeln("---", source = str(i), prefix = " X")


    def __enter_scene__(self, *args, **kwargs):
        #print("Entered convo with", kwargs['target'])
        self.current_target = kwargs['target']

        self.convo_data = self.state.conversations.get(kwargs['target'])
        self.__next_stage__(kwargs.get('stage', None) or "start")

    def __exit_scene__(self, *args, **kwargs):
        pass

    def __autocomplete__(self):
        acd = {}
        for choice in self.convo_data.get(self.current_stage, {}).get("options", {}).keys():
            acd[choice] = None
        return acd

    def read(self, line):
        opts = list(self.convo_data[self.current_stage].get("options", {}).keys())
        outputs = self.convo_data[self.current_stage].get("options", {})

        # Assume key is explicit
        key = line

        # If key is just a number and not one of the options...
        if key not in opts and line.isnumeric():
            index = int(line)
            # And within the range of the options
            if index >= 0 and index < len(opts):
                # Get the key at that inex
                key = opts[index]

        # If key doesn't exist, try and find the nearest match key
        if key not in opts:#TODO collect matches and only pass if theres 1 result
            matches = []
            for opt in opts:
                if opt.lower().startswith(key):
                    matches.append(opt)

            if len(matches) >= 1:
                key = matches[0]

        if key not in opts:
            return self.state.writeln("What?")
        else:
            if not self.handle_conditional(key):
                return self.state.writeln("Can't do that.")
            targets = outputs[key]
            for target in targets.split("||"):
                target = target.strip()
                match target:
                    case "end":
                        self.state.clear_scene()

                    case target if target.startswith("next "):
                        self.__next_stage__(" ".join(target.split(" ")[1:]))

                    case target if target.startswith("inc "):
                        kv = " ".join(target.split(" ")[1:]).strip()
                        n = 1
                        if " " in kv:
                            n = int(kv.split(" ")[1])
                            kv = kv.split(" ")[0]

                        self.state.set_var(kv, self.state.touch_var(kv, 0) + n)

                    case target if target.startswith("dec "):
                        kv = " ".join(target.split(" ")[1:]).strip()
                        n = 1
                        if " " in kv:
                            n = int(kv.split(" ")[1])
                            kv = kv.split(" ")[0]

                        self.state.set_var(kv, self.state.touch_var(kv, 0) - n)

                    case target if target.startswith("set "):
                        kv = " ".join(target.split(" ")[1:]).strip()
                        key = kv.split("=")[0].strip()
                        val = self.state._eval_code(" ".join(kv.split("=")[1:]).strip())
                        #if val == "True": val = True
                        #if type(val) == str and val.isnumeric(): val = int(val)
                        print(key, val, type(val))
                        self.state.set_var(key, val)

                    case target if target.startswith("reply "):
                        self.state.writeln(" ".join(target.split(" ")[1:]), source = f"{self.convo_data.get('_speaker', '???')}")
def __connect__():
    pass

XYZZY = {
    "scenes": [Convo],

}
