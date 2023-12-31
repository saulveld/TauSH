import readline
import os
import sys
from types import ModuleType

def get_tree_options(already, tree, rtn, path=None):
    if tree not in already and isinstance(tree, dict):
        already.append(tree)
        for i in [str(k) for k in tree.keys()]:
            if path is None:
                new_path = i
            else:
                new_path = f"{path}.{i}"
            if new_path not in rtn:
                rtn.append(new_path)
                get_tree_options(already, tree[i], rtn, new_path)
        
def get_code_options(already, path, rtn):
    already.append(".".join(path))
    for i in eval(f'dir(path)'):
        if not i.startswith("_"):
            new_path = path + [i]
            rtn.append(".".join(new_path[1:]))

class Completer(object):  # Custom completer
    def __init__(self, dictionary):
        self.dictionary = dictionary
    
    def modules(self):
        return self.dictionary["modules"]

    def complete(self, text, state):
        if state == 0:  # on first trigger, build possible matches
            if not text:
                self.matches = self.options[:]
            else:
                if "." in text:
                    heads = text.split(".")[:-1]
                    tail = text.split(".")[-1]
                    cur = self.dictionary
                    for i in heads:
                        cur = cur.get(i, None)
                        if cur is None:
                            break
                    
                    if cur != None:
                        keys = [str(k) for k in cur.keys()]
                        matching_keys = filter(lambda f: f.startswith(tail), keys)
                        self.matches = list(map(lambda k: f"{'.'.join(heads + [k])}", matching_keys))
                    else:
                        self.matches = list(map(lambda t: f"{'.'.join(heads + [t])}", filter(lambda x: x.startswith(tail), eval(f"dir({'.'.join(heads)})"))))
                else:
                    self.matches = list(map(lambda x: f"'{x}'", filter(lambda f: f.startswith(text), os.listdir())))
                    
                    for m in self.modules():
                        self.matches += list(filter(lambda f: f.startswith(text), dir(m)))
                
        # return match indexed by state
        try:
            if len(self.matches) > state:
                return self.matches[state]
            else:
                return None
        except IndexError:
            return None

    def display_matches(self, substitution, matches, longest_match_length):
        line_buffer = readline.get_line_buffer()
        columns = os.environ.get("COLUMNS", 80)

        print()

        tpl = "{:<" + str(int(max(map(len, matches)) * 1.2)) + "}"

        buffer = ""
        for match in matches:
            match = tpl.format(match[len(substitution):])
            if len(buffer + match) > columns:
                print(buffer)
                buffer = ""
            buffer += match

        if buffer:
            print(buffer)

        print("> ", end="")
        print(line_buffer, end="")
        sys.stdout.flush()


