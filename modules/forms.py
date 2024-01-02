import sys
_environ_ = {}	

class FormItem:
  def __init__(self, **kwargs):
    self.properties = kwargs
    self.children = kwargs.get("children", [])
    self.name = kwargs.get("name", "")
    self.parent = None
    self._last_value = None
    self.on_refresh = None
  
  def state(self, path=None):
    if self.parent != None:
      return self.parent.state(path)
    return self.value(path)
    
  def __dict__(self):
    return self.state(self.path())
  
  def last_value(self, path=None):    
    if self.parent != None:
      return self.parent.last_value(path)
    host = self._last_value
    if host == None:
      return None
    if path == None:
      return host
    for step in path:
      host = host.get(step, None)
      if host == None:
        return None
    return host
  
  def last_state(self, path=None):
    if self.parent != None:
      return self.parent.last_state(path)
    return self.last_value(path)
  
  def value(self, path=None):
    if path == None:
      rtn = {}
      for child in self.children:
        rtn[child.name] = child.value
      return rtn
    else:
      host = self
      for step in path:
        host = host.__dict__.get(step, None)
        if host == None:
          return None
      return host.value
    
  def path(self):
    if self.parent != None:
      return self.parent.path() + [self.name]
    return None

  def refresh(self):
    self.last_state()
    for child in self.children:
      child.refresh()
    if self.on_refresh != None:
      self.on_refresh(self)

class Form(FormItem):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
  
class DefaultedValue(FormItem):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.value = kwargs.get("value", None)
    self.default = kwargs.get("default", None)
  
  def value(self):
    if self.last_state() == None:
      return self.properties["default"](None)
    return self.properties["value"](self.last_state())

class Input(DefaultedValue):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)

class Toggle(DefaultedValue):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
  
class Single(DefaultedValue):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)

class Multiple(FormItem):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)

  def value(self):
    if self.last_state() == None:
      return self.properties["default"](None)
    return self.properties["values"](self.last_state())

class Area(DefaultedValue):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)

class Action(FormItem):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.action = kwargs.get("action", None)
  
  def __call__(self, *args):
    current = self.action
    for arg in args:
      current = current(arg)
    return current  

class Chain(FormItem):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

class Dual(DefaultedValue):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

class Text(DefaultedValue):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)

def form(*args):
  return getattr(sys.modules[__name__], args[0])(*args[1:-1], **args[-1])
  
def on_load(d):
  global _environ_
  _environ_ = d
  d["lisp"] = d["lisp"] | {"form": form}

# a submission is a form.__dict__()
# this dictionary is the submission.
# make them all predicates and load them from the db.
# form_handler which is a function that takes a form and runs it in its own thread.
# the form handler is responsible for the submission.