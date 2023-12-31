import os
import shutil
import re


def ls(*a):
  return os.listdir(*a)


def cd(*a):
  return os.chdir(*a)


def pwd(*a):
  return os.getcwd(*a)


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


def lines(items):
  return '\n'.join(items)


def echo(*a):
  return ' '.join([str(i) for i in a])