import os
import shutil
import re

def ls(*a):
  if len(a) > 0:
    return lines(os.listdir(str(a[0])))
  return lines(os.listdir())


def cd(*a):
  return os.chdir(str(a[0]))


def pwd(*a):
  return os.getcwd()


def mkdir(*a):
  return os.mkdir(str(a[0]))


def rm(*a):
  return os.remove(str(a[0]))


def rmdir(*a):
  return os.rmdir(str(a[0]))


def mv(*a):
  return os.rename(str(a[0]))


def cp(*a):
  return shutil.copy(str(a[0]))


def exp(*a):
  return os.system(f"explorer {''.join([str(i) for i in a])}")


def where(input, pattern):
  patter = str(pattern)
  rtns = []
  if isinstance(input, list):
    for i in input:
      if re.search(pattern, i) is not None:
        rtns.append(i)
  else:
    if re.search(pattern, input) is not None:
      rtns.append(input)
  return rtns


def lines(items):
  return '\n'.join(items)


def echo(*a):
  return ' '.join([str(i) for i in a])

def on_load(instance):
  print ("Loaded std module")