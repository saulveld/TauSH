import readline
import Completer
import atexit
import util

if __name__ == "__main__":
  util.initialize_environment("_environ_.json")
  completer = Completer.Completer(util._environ_)
  try:
    readline.read_history_file(util._environ_["history"]["file"])
    readline.set_completer(completer.complete)
    readline.parse_and_bind("tab: complete")
  except FileNotFoundError:
    pass
  atexit.register(readline.write_history_file, util._environ_["history"]["file"])
  util.repl()
