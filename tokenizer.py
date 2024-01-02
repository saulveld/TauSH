class Tokenizer:
  def __init__(self, create_part, create_call, binaries = [],  segments = [],  prefixes = []):
    self.create_part = create_part
    self.create_call = create_call
    self.binaries = binaries
    self.segments = segments
    self.prefixes = prefixes
    self.token = ""
    self.index = -1
    self.tokens = []
    self.builders = []

  def append(self, token):
    self.tokens.append(token)
    if len(self.builders) > 0:
      if len(self.tokens) - self.builders[-1][1] == self.builders[-1][0]:
        self.tokens[self.builders[-1][1]] = self.builders[-1][2](*self.tokens[self.builders[-1][1]:])
        self.tokens = self.tokens[:self.builders[-1][1] + 1]
        self.builders.pop()
    self.token = ""
  
  def set_builder(self, c):
    for char, count, fact in self.prefixes:
        if c == char:
          self.builders.append((count, len(self.tokens), fact))
          return  True
    return False
  
  def build_binary(self, c, s):
    for char, fact in self.binaries:
      if c == char:
        left = self.create_call(*self.tokens) if len(self.tokens) > 1 else self.tokens[-1]
        right = Tokenizer(self.create_part, self.create_call, self.binaries, self.segments, self.prefixes).tokenize(s[(self.index + 1):])
        return fact(left, right)
    return None
  
  def build_segment(self, c):
    for open_c, close_c, fact in self.segments:
          if self.token.startswith(open_c):
            if c == close_c:
              self.append(fact(self.token[1:]))
              return True
    return False
  
  def tokenize(self, s):
    for c in s:
      self.index += 1
      if self.token == "":
        if not c.isspace():
          if not self.set_builder(c):
            b = self.build_binary(c, s)
            if b is not None:
              return b          
            self.token += c
      else:
        if not self.build_segment(c):
          if c.isspace():
            self.append(self.create_part(self.token))
            if len(self.builders) > 0:
              if len(self.tokens) - self.builders[-1][1] == self.builders[-1][0]:
                self.tokens[self.builders[-1][1]] = self.builders[-1][2](*self.tokens[self.builders[-1][1]:])
                self.tokens = self.tokens[:self.builders[-1][1] + 1]
                self.builders.pop()
            self.token = ""
          else:
            self.token += c
    if self.token != "":
      self.append(self.create_part(self.token))
    return self.create_call(*self.tokens)