import pickle
import sys
import re
import readline
import json
import os
import importlib.util
import subprocess

_newline_ = "\n"
_environ_file_ = "_environ_.json"
_default_history_ = {"file": "history.txt", "length": 1000}
_default_init_ = {"file":"init.tau", "modules":["std.py"]}
_environ_ = json.load(open(_environ_file_))
_environ_stack_ = [_environ_]
_current_ = ""

def get_command(name):
  for m in _environ_["modules"]:
    if hasattr(m, name):
      command = getattr(m, name)
      if callable(command):
        return command
  return None

def get_object(name):
  for m in _environ_["modules"]:
    if hasattr(m, name):
      return getattr(m, name)

def coalesce(*args):
  for arg in args:
    if arg is not None:
      return arg
  return None

def clean_string_end(s):
  if s is None or len(s) < 1:
    return None
  while s[-1] in "\r\n\t ":
    s = s[:-1]
  return s

def cmd(*a):
  proc = subprocess.Popen([str(item) for item in a], stdout=subprocess.PIPE, shell=True)
  (out, err) = proc.communicate()
  return clean_string_end(out.decode("utf-8"))

class CommandPart:
  word_types = []
  def __init__(self, s):
    self.text = s

  def __str__(self):
    return str(self())
  
  def __call__(self, *args):
    return self.text
  
  #def __call__(self, *args):
  #  return coalesce(self.data, self.command, self.name)
  
  def set_value(self, value):
    _environ_[self.text] = value

  @classmethod
  def add_word_type(cls, t):
    cls.word_types.append(t)

  @classmethod
  def create(cls, value):
    for wt in cls.word_types:
      if wt.is_acceptable_input(value):
        return wt(value)
    return CommandPart(value)

class CallablePart(CommandPart):
  def __init__(self, s):
    super().__init__(s)

class Access(CallablePart):
  def __init__(self, text):
    super().__init__(text)
    self.chain = [CommandPart.create(part) for part in text.split(".")]

  def __call__(self, *args):
    if len(self.chain) > 0:
      current = self.chain[0]
      if callable(current):
        current = current()
    for step in self.chain[1:]:
      if not isinstance(current, dict):
        current = current.__dict__
      current = current.get(str(step), None)
      if current is None:
        print (f"Error: {str(current)} does not have attribute {step}")
    return current

  def set_value(self, value): 
    if len(self.chain) > 0:
      current = self.chain[0]()
    for step in self.chain[1:-1]:
      if hasattr(current, str(step)):
        current = getattr(current, str(step))
      else:
        print (f"Error: {str(current)} does not have attribute {step}")
    setattr(current, str(self.chain[-1]), value)

  @classmethod
  def is_acceptable_input(cls, inp):
    if isinstance(inp, str):
      return re.search(r"\.[a-zA-Z_]", inp) != None
    else:
      return False

  class CodeCall(CallablePart):
    def __init__(self, text, command):
      super().__init__(text)
      self.command = command

    def __call__(self, *args):
      return self.command(*args)
    
    @classmethod
    def is_acceptable_input(cls, inp):
      _environ_.modules[0].__dict__.keys()
    
  
  class CommandCall(CallablePart):
    def __init__(self, text):
      super().__init__(text)
    
    def __call__(self, *args):
      return cmd([self.text] + [str(a) for a in args])

CommandPart.add_word_type(Access)

class Variable(CommandPart):
  def __init__(self, text):
    if isinstance(text, Variable):
      text = text.text
    if text.startswith("@"):
      text = text [1:]
    super().__init__(text)
  
  def __str__(self):
    return _environ_[self.text]
  
  def __call__(self):
    return _environ_[self.text]
  
  @classmethod
  def is_acceptable_input(self, text):
    if isinstance(text, str):
      return text.startswith("@") or text in _environ_.keys()
    elif isinstance(text, Variable):
      return True
  
CommandPart.add_word_type(Variable)

class CommandReference(CallablePart):
  def __init__(self, text):
    super().__init__(text)
    self.command = get_command(text)
  
  def __call__(self, *args):
    try:
      if callable(self.command):
        return self.command(*args)
      else:
        return self.command
    except Exception as e:
      print(f"Error: {str(self.text)} Threw: {str(e)}")
      return None
    
  def __str__(self):
    return self.text
  
  @classmethod
  def is_acceptable_input(self, inp):
    cmd = get_command(inp)
    if cmd is not None:
      return True
    else:
      return False
    
CommandPart.add_word_type(CommandReference)      

class ObjectReference(CommandPart):
  def __init__(self, text):
    super().__init__(text)
    self.data = get_object(text)
  
  def __call__(self, *args):
    return self.data
  
  def __str__(self):
    return self.text
  
  @classmethod
  def is_acceptable_input(self, inp):
    return get_object(inp) is not None
  
CommandPart.add_word_type(ObjectReference)

class ExternalCommand(CommandPart):
  def __init__(self, text):
    super().__init__(text)

  def __call__(self, *args):
    return cmd(*[self.text] + [str(arg) for arg in args])

  def __str__(self):
    return self.text

  @classmethod
  def is_acceptable_input(cls, inp):
    return True

class Segement(CommandPart):
  def __init__(self, start, stop):
    self.start = start
    self.stop = stop

class String(CommandPart):
  def __init__(self, s):
    super().__init__(s)

  def __str__(self):
    return self.text

class Interpolation(CommandPart):
  def __init__(self, s):
    super().__init__(s)
    self.value = s

  def __str__(self):
    r = self()  
    if r is None:
      return ""
    else:
      return r
  
  def __call__(self, *args):
    return evaluate(self.value)
  
class ShellStatement:
  binaries = []
  segments = []
  def __init__(self, action, arguments):
    self.action = action
    self.arguments = [a for a in arguments]

  def inject_argument(self, argument):
    self.arguments = [argument] + self.arguments

  @classmethod
  def add_binary(cls, char, fcls):
    cls.binaries.append((char, fcls))
  
  @classmethod
  def add_segment(cls, open_char, close_char, fact):
    cls.segments.append((open_char, close_char, fact))

  @classmethod
  def tokenize(cls, s):
    tokens = []
    token = ""
    index = -1
    for c in s:
      index += 1
      if token == "":
        if not c.isspace():
          for char, fact in cls.binaries:
            if c == char:
              left = ShellCall(*tokens) if len(tokens) > 1 else tokens[-1]
              right = ShellStatement.tokenize(s[(index + 1):])
              return fact(left, right)
          token += c
      else:
        found = False
        for open_c, close_c, fact in cls.segments:
          if token.startswith(open_c):
            if c == close_c:
              tokens.append(fact(token[1:]))
              token = ""
              found = True
        if not found:
          if c.isspace():
            tokens.append(CommandPart.create(token))
            token = ""
          else:
            token += c
    if token != "":
      tokens.append(CommandPart.create(token))
    return ShellCall(*tokens)

class ShellCall(ShellStatement):
  def __init__(self, *args):
    self.arguments: [CommandPart] = [a for a in args]

  def inject_argument(self, argument):
    self.arguments = [self.head(), argument] + self.tail()

  def __str__(self):
    return " ".join([str(a) for a in self.arguments])

  def head(self):
    return self.arguments[0]
  
  def tail(self):
    if len(self.arguments) < 2:
      return []
    return [str(x) for x in self.arguments[1:]]
  
  def callable_head(self):
    if isinstance(self.head(), Access):
      return self.head()()
    if isinstance(self.head(), CallablePart):
      return self.head()
    else:
      return ExternalCommand(self.head().text)

  def __call__(self, *args):
    return self.callable_head()(*self.tail())

class Pipe(ShellStatement):
  def __init__(self, *statements: [ShellStatement]):
    self.statements = statements
  
  def __call__(self, *args: [CommandPart]):
    index = 0
    while index < (len(self.statements) - 1):
      self.statements[index + 1].inject_argument(self.statements[index]())
      index += 1
    return self.statements[-1]()

class Set(ShellStatement):
  def __init__(self, left, right):
    self.left  = left
    self.right = right

  def inject_argument(self, argument):
    self.right = str(argument)
  
  def __call__(self, *args):
    return self.left.set_value(str(self.right))
  
ShellStatement.add_binary("|", Pipe)
ShellStatement.add_binary("=", Set)
ShellStatement.add_segment("'", "'", String)
ShellStatement.add_segment('"', '"', String)
ShellStatement.add_segment("{", "}", Interpolation)

def count_chars(c, s):
  count = 0
  for char in s:
    if char == c:
      count += 1
  return count

def still_open(o, c):
  if o == c:
    return count_chars(o, _current_) % 2 != 0
  else:
    return count_chars(o, _current_) > count_chars(c, _current_)

def entry_incomplete():
  return any([still_open(o, c) for o, c, _ in ShellStatement.segments])

def is_quitting():
  return _current_.lower() == "quit"

def continue_prompt():
  global _current_
  _current_ += input(f'{str(count_chars(_newline_, _current_))}') + _newline_

def initial_prompt():
  global _current_
  _current_ = input(ShellStatement.tokenize(_environ_["prompt"])())  

def repl():
  global _current_
  initial_prompt()
  while not is_quitting():
    if not entry_incomplete():
      run_current()
      initial_prompt()
    else: 
      _current_ += _newline_
      continue_prompt()


def run_file(f):
  global _current_
  lines = open(f).readlines()
  for line in lines:
    _current_ += line
    if entry_incomplete():
      _current_ += _newline_
    else:
      run_current()


def run_current():
  global _current_
  out = ShellStatement.tokenize(_current_)()
  _current_ = ""
  if out is not None:
    print(out)


def load(*a):
  # load a module into modules
  local_modules = os.listdir(_environ_["module_dir"])
  for item in a:
    if item in local_modules:
      if item.endswith(".py"):
        name = item.split(".")[0]
        path = f'{_environ_["module_dir"]}/{item}'
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _environ_["modules"].append(mod)
        _environ_[name] = mod
      elif a.endswith(".tau"):
        run_file(f'{_environ_["module_dir"]}/{item}')
    else:
      _environ_[item] = __import__(item)
      _environ_["modules"].append(_environ_[item] )
      _environ_["modules"][0].__dict__[item] = _environ_[item]


def evaluate(s):
  try:
    if "\n" in s:
      exec(s, _environ_["modules"][0].__dict__)
      return None
    else:
      c = compile(s, '', 'eval')
      r = eval(c)
      return str(r)
  except Exception as e:
    print(f"Error: {str(e)}")
    return None
  

def runpy(item):
  return exec(open(item).read())


def save(*a):
  # save the current environment to a file
  if len(a) == 0:
    pickle.dump(_environ_, open("taush.pkl", "wb"))
  elif len(a) == 1:
    pickle.dump(_environ_, open(a[0], "wb"))
  elif len(a) == 2:
    pickle.dump(a[0](), open(*a[1:], "wb"))
  else:
    print("Error: save takes 0, 1, or 2 arguments")


def resume(*a):
  # resume the environment from a file
  if len(a) == 0:
    _environ_ = pickle.load(open("taush.pkl", "rb"))
  elif len(a) == 1:
    _environ_ = pickle.load(open(a[0], "rb"))
  elif len(a) == 2:
    _environ_[str(a[0])] = pickle.load(open(*a[1:], "rb"))
  else:
    print("Error: resume takes 0, 1, or 2 arguments")


def push(*a):
  _environ_stack_.append(_environ_.copy())
  return "Environment Copy Stacked"
  

def pop(*a):
  _environ_ = _environ_stack_.pop()
  return "Environment Copy Popped"

_environ_["modules"] = [sys.modules[__name__]] + _environ_["modules"]
_environ_["env"] = _environ_

if __name__ == "__main__":
  try:
    readline.read_history_file(_environ_.get("history", _default_history_ )["file"])
    readline.set_history_length(_environ_.get("history", _default_history_ )["length"])
  except FileNotFoundError:
    pass

  for module in _environ_.get("init", _default_init_)["modules"]:
    load(module)

  run_file(_environ_.get("init", _default_init_)["file"])
  repl()
