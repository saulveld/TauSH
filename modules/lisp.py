# this is the lisp
from functools import reduce
import sys
sys.path.append("./modules")
import parts
import os
import shutil
import re

_image_ = {}

class Lisp(parts.CallablePart):
  def __init__(self, s):
    super().__init__(s)
    self.value = s

  def __str__(self):
    return self.value
  
  def __call__(self, *args):
    return lisp(self.value, _image_["lisp"])

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
    if isinstance(string, list):
      atoms_to_lisp(string)
    else:
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

def on_load(mdict):
  global _image_
  _image_ = mdict
  mdict["lisp"] = mdict["lisp"] | {
    "print": print,
    "ls": os.listdir,
    "cd": os.chdir,
    "pwd": os.getcwd,
    "mkdir": os.mkdir,
    "rm": os.remove,
    "rmdir": os.rmdir,
    "mv": os.rename,
    "cp": shutil.copy,
    "exp": lambda *a: os.system(f"explorer {''.join([str(i) for i in a])}"),
    "where": lambda input, lam: filter(lam, input),    
    "map": lambda input, lam: map(lambda a,b: lam(a)(b), input),    
    "reduce": lambda input, lam: reduce(lam, input),    
    "\\" : lambda *a: lambda x: taush.dowith(lisp(a[1:], **{a[0].text:x}))
  }
  mdict["statement"]["segments"].append(("[", "]", Lisp))