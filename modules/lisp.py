# this is the lisp
import taush

class Lisp(taush.CommandPart):
  def __init__(self, s):
    super().__init__(s)
    self.value = s

  def __str__(self):
    return self.value
  
  def __call__(self, *args):
    return lisp(self.value, taush._environ_["lisp"])

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

taush.ShellStatement.add_segment("[", "]", Lisp)