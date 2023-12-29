import pickle
import sys
import os
import shutil
import re

_environ_stack_ = []
_environ_ = {
    "modules": [],
    "prompt_prefix": "|",
    "prompt_suffix": "|>",
    "prompt": "pwd",
    }

def ls(*a):
  return os.listdir(*a)


def cd(*a):
  return os.chdir(*a)


def pwd(*a):
  return os.getcwd(*a)


def cmd(*a):
  return os.system(*a)


def mkdir(*a):
  return os.mkdir(*a)


def rm(*a):
  return os.remove(*a)


def rmdir(*a):
  return os.rmdir(*a)


def mv(*a):
  return os.rename(*a)


def cp(*a):
  return shutil.copy(*a)


def exp(*a):
  return os.system(f"explorer {''.join(a)}")


def where(input, pattern):
  rtns = []
  if isinstance(input, list):
    for i in input:
      if re.search(pattern, i) is not None:
        rtns.append(i)
  else:
    if re.search(pattern, input) is not None:
      rtns.append(input)
  return rtns


def interpolate(s):
  prefix = s.split("{")[0]
  code = s.split("{")[1].split("}")[0]
  suffix = s.split("}")[1]
  return f"{prefix}{eval(code)}{suffix}"


def lines(items):
  return '\n'.join(items)


def get_command(*a):
  for m in _environ_["modules"]:
    if hasattr(m, a[0]):
      command = getattr(m, a[0])
      def rtn(*args):
        try:
          return command(*args)
        except Exception as e:
          print(f"Error: {a[0]} Threw: {str(e)}")
          return None
        
    if callable(command):
      return rtn
    else:
      return command
  return None


class Word:
  def __init__(self, s):
    self.value = s

  def __str__(self):
    return self.value
  
  def __call__(self, *args):
    return get_command(self.value)


class String:
  def __init__(self, s):
    self.value = s

  def __str__(self):
    return self.value


class Interpolation:
  def __init__(self, s):
    self.value = s

  def __str__(self):
    r = self()  
    if r is None:
      return ""
    else:
      return r
  
  def __call__(self, *args):
    return evaluate(self.value)


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

class ShellCall:
  def __init__(self, *args):
    self.args = args  

  def __call__(self, *args):
    if isinstance(self.args[0], Interpolation):
      return self.args[0](*args)
    command = self.args[0]()
    if command is not None:
      input = []
      if len(args) > 0:
        input += args
      if len(self.args) > 1:
        input += [str(x) for x in self.args[1:]]
        if callable(command):
          return command(*input)  
        return command
    else:
      return cmd(''.join([str(p) for p in self.args]))
  

class Pipe:
  def __init__(self, left, right):
    self.left = left
    self.right = right
  
  def __call__(self, *args):
    return self.right(self.left(*args))


class Access:
  def __init__(self, chain):
    self.chain = chain
  
  def __call__(self, *args):
    if len(self.chain) > 0:
      current = self.chain[0](*args)
    for step in self.chain[1:]:
      if hasattr(current, str(step)):
        current = getattr(current, str(step))
      else:
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
  

class Variable:
  def __init__(self, name):
    self.name = name
  
  def __call__(self, *args):
    return _environ_[self.name]
  
  def __str__(self):
    return _environ_[self.name]
  
  def set_value(self, value):
    _environ_[self.name] = value


class Set:
  def __init__(self, left, right):
    self.left = left
    self.right = right
  
  def __call__(self, *args):
    self.left.set_value(self.right(*args))
    return self.left(*args)
 

def tokenize(s):
  def factory(s):
    parts = list(map(lambda p: Variable(p[1:]) if p.startswith("@") else Word(p), s.split(".")))
    if len(parts) > 1:
      return Access(parts)
    else:
      return parts[0]
  tokens = []
  token = ""
  index = -1
  for c in s:
    index += 1
    if token == "":
      if not c.isspace():
        if c == "|":
          return Pipe(ShellCall(*tokens), tokenize(s[(index + 1):]))
        token += c
    elif token.startswith('{'):
      token += c
      if c == '}':
        tokens.append(Interpolation(token[1:-1]))
        token = ""
    elif token.startswith("'"):
      token += c
      if c == "'":
        tokens.append(String(token[1:-1]))
        token = ""
    elif c.isspace():
      if token != "":
        tokens.append(factory(token))
        token = ""
    else:
      token += c
  if token != "":
    tokens.append(factory(token))
  return ShellCall(*tokens)


def prmpt():
  return input(f"{Variable('prompt_prefix')()}{tokenize(_environ_['prompt'])()}{Variable('prompt_suffix')()}")


def cont():
  return input("...")


def count_chars(c, s):
  count = 0
  for char in s:
    if char == c:
      count += 1
  return count


def repl():
  in_interpolation = False
  complete = False
  raw = prmpt()
  while not complete:
    opens = count_chars("{", raw)
    closes = count_chars("}", raw)
    in_interpolation = opens > closes
    if not in_interpolation:
      if raw.lower() == "quit":
        complete = True
      else:
        out = tokenize(raw)()
        if out is not None:
          print(out)
        raw = prmpt() 
    else: 
      raw += cont() + "\n"


def echo(*a):
  return ' '.join(a)


def set(*a):
  return os.environ.__setitem__(*a)

 
def load(*a):
  # load a module into modules
  _environ_[a[0]] = __import__(*a)
  _environ_["modules"].append(_environ_[a[0]] )
  _environ_["modules"][0].__dict__[a[0]] = _environ_[a[0]]


def runpy(*a):
  # run a script
  exec(open(*a).read())


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

_environ_["modules"] = [sys.modules[__name__]]
_environ_["env"] = _environ_

if __name__ == "__main__":
  repl()

# i could be a pickle or a file or a pip module.