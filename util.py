import os
import importlib.util
import subprocess
import pickle 
import json
import sys
from proxydictionary import ProxyDict
from tokenizer import Tokenizer

_environ_ = {}
_environ_stack_ = []
_current_ = ""
_newline_ = "\n"

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
  return any([still_open(o, c) for o, c, _ in _environ_["statement"]["segments"]])

def is_quitting():
  return _current_.lower() == "quit"

def continue_prompt():
  global _current_
  _current_ += input(f'{str(count_chars(_newline_, _current_))}') + _newline_

def initial_prompt():
  global _current_
  _current_ = input(tokenize(_environ_["prompt"])())  

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

def tokenize(s):
  return Tokenizer(**_environ_["statement"]).tokenize(s)

def run_current():
  global _current_
  try:
    out = tokenize(_current_)()
    _current_ = ""
    if out is not None:
      print(out)
  except Exception as e:
    print(f"Error: {str(e)}")
    _current_ = ""

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
        if len(a) > 1:
          _environ_[a[1].text] = mod
        mod.on_load(_environ_)
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
      r = eval(c, _environ_["modules"][0].__dict__, _environ_)
      return str(r)
  except Exception as e:
    print(f"Error: {str(e)}")
    return None

def lisp(s, d):
  def string_lisp(string):
    def atoms_to_lisp(atoms):
      items = []
      for i, atom in enumerate(atoms):
        if atoms == '[':
          items += atoms_to_lisp(atoms[i+1:])
        elif atoms[0] == ']':
          items = [items]
        else:
          items.append(atom)
      return items
    atoms_to_lisp(string.replace('[', ' [ ').replace(']', ' ] ').split())
  def run(l):
    if isinstance(l, list):
      if not isinstance(l[0], list):
        v = d.get(l[0], None)         
        if v is not None and callable(v):
          return v(*[run(i) for i in l[1:]])
      else:
        return [run(i) for i in l]
    else:
      v = d.get(l, None)
      if v is not None:
        if callable(v):
          return v()
        else:
          return v
      else:
        return l
  return run(string_lisp(s))  

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

def push(**kwargs):
  _environ_stack_.append(ProxyDict(_environ_, **kwargs))
  
def pop(*a):
  _environ_ = _environ_stack_.pop()
  return "Environment Copy Popped"

def dowith(f, **kwargs):
  push(**kwargs)
  rtn = f()
  pop()
  return rtn

def initialize_environment(file_name):
  global _environ_
  _environ_ = json.load(open(file_name, "r"))
  _environ_["modules"] = [sys.modules[__name__]] + _environ_["modules"]
  _environ_["env"] = _environ_
  for module in _environ_["init"]["modules"]:
    load(module)
  run_file(_environ_["init"]["file"])