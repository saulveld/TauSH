class ProxyDict(dict):
  def __init__(self, original, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.__dict__ = dict(**kwargs)
    self.original = original
  
  def __getattr__(self, name):
    return self.get(name, self.original[name])

  