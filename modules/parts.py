from tokenizer import Tokenizer
from util import get_command, get_object, coalesce, cmd, evaluate, dowith
import re

_environ_ = {}

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
      current = current.get(step.text, None)
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
    if isinstance(text, CommandPart):
      text = text.text
    if text.startswith("@"):
      text = text [1:]
    super().__init__(text)
  
  def __str__(self):
    return _environ_.get(self.text, self.text)
  
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
    return self.value
  
  def __call__(self, *args):
    return evaluate(self.value)
  
class ShellStatement:
  def __init__(self, action, arguments):
    self.action = action
    self.arguments = [a for a in arguments]

  def inject_argument(self, argument):
    self.arguments = [argument] + self.arguments

  @classmethod
  def add_binary(cls, char, fcls):
    _environ_["statement"]["binaries"].append((char, fcls))
  
  @classmethod
  def add_segment(cls, open_char, close_char, fact):
    _environ_["statement"]["segments"].append((open_char, close_char, fact))

  @classmethod
  def add_prefix(cls, char, count, fact):
    _environ_["statement"]["prefixes"].append((char, count, fact))

  @classmethod
  def tokenize(cls, s):
    return Tokenizer(CommandPart.create, ShellCall, _environ_["statement"]["binaries"], _environ_["statement"]["segments"], _environ_["statement"]["prefixes"]).tokenize(s)
    
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
  
class Lambda(CallablePart):
  def __init__(self, name, interior_part):
    super().__init__(name)
    self.interior_part = interior_part
    
  def __call__(self, *args):
    return dowith(self.interior_part, **{self.name:args[0]()})
 
  def __str__(self):
    return f"lambda ({','.join([str(a) for a in self.arguments])}): {str(self.body)}"

def on_load(data):
  global _environ_
  _environ_ = data
  _environ_["statement"]["create_part"] = CommandPart.create
  _environ_["statement"]["create_call"] = ShellCall
  _environ_["statement"]["prefixes"].append(("\\", 2, Lambda))
  _environ_["statement"]["binaries"].append(("|", Pipe))
  _environ_["statement"]["binaries"].append(("=", Set))
  _environ_["statement"]["segments"].append(("'", "'", String))
  _environ_["statement"]["segments"].append(('"', '"', String))
  _environ_["statement"]["segments"].append(("{", "}", Interpolation))
  