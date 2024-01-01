import sqlite3
import taush

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def _quote(v):
  return f"'{v}'"

class Argument:
  def __init__(self, argument_number, argument_type, value):
    self.argument_type = argument_type
    self.value = value

class PredicateArgument(Argument):
  table_name = "predicate_arguments"
  fields = ["query_id", "argument_number", "argument", "argument_type"]
  def __init__(self, argument_number, argument_type, value):
    super().__init__(argument_number, argument_type, value)

class RuleArgument(Argument):
  table_name = "rule_arguments"
  fields = ["rule_id", "argument_number", "argument", "argument_type"]
  def __init__(self, argument_number, argument_type, value):
    super().__init__(argument_number, argument_type, value)

  def to_sql(self):
    if self.argument_type == 'VAR':
      return self.value
    else:
      return f"'{self.value}'"

class QueryArgument(Argument):
  table_name = "query_arguments"
  fields = ["query_id", "argument_number", "argument", "argument_type"]
  def __init__(self, argument_number, argument_type, value):
    super().__init__(argument_number, argument_type, value)

class Query:
  table_name = "queries"
  fields = ["query_id", "rule_id", "sequence", "predicate_id"]
  def __init__(self, query_id, rule_id, sequence, predicate_id):
    self.query_id = query_id
    self.rule_id = rule_id
    self.sequence = sequence
    self.predicate_id = predicate_id
    self.arguments = []
    self.db = None

  def to_sql(self) -> str:
    return self.db.predicates[self.predicate_id].query(self.arguments)

class Rule:
  table_name = "rules"
  fields = ["rule_id", "predicate_id"]
  def __init__(self, predicate, arguments, queries: [[(str, str)]]):
    self.id = -1
    self.predicate = predicate
    self.predicate.rules[self.id] = self 
    self.arguments = [Argument(i, argument_type, value) for i, (argument_type, value) in enumerate(arguments)]
    self.queries = [Query(self, i, qargs) for i, qargs in enumerate(queries)]
    self.db = None
    self.predicate = None

  def attach(self, db):
    self.db = db
    self.db.rules[self.id] = self
    self.predicate = self.db.predicates[self.predicate_id]


  def wrapping_sql(self, innersql):
    select_items = [f"{a.to_sql()}  as {self.pred.part_name(a.argument_number)}" for a in self.arguments]
    return f"select {', '.join(select_items)} from ({innersql})"
  
  def to_sql(self) -> str:
    last_query = None
    sql = " from "
    for query in self.queries:
      if last_query is None:
        sql += f" from ({query.to_sql()}) as Q{query.query_id}"
      else:
        last_query_vars = filter(lambda a: a.argument_type == "VAR", last_query.arguments)
        query_vars = filter(lambda a: a.argument_type == "VAR", query.arguments)
        shared = list(set(last_query_vars) & set(query_vars))
        joins = [f"Q{last_query.query_id}.{s} = {query.query_id}.{s}" for s in shared]
        sql += f" join ({query.to_sql()}) as Q{query.query_id} on {' and '.join(joins)}"
    return sql    

class Predicate:
  table_name = "predicates"
  fields = ["predicate_id", "name", "arity", "table_name"]
  def __init__(self, predicate_id, name, arity, table_name):
    self.predicate_id = predicate_id
    self.name = name
    self.arity = arity
    self.table_name = table_name
    self.rules = []
    self.parts = []
    self.db = None
    self.query_hook = None
    self.fact_hooks = []
  
  def attach(self, db):
    self.db = db
    self.db.predicates[self.predicate_id] = self

  def part_name(self, part_number):
    for part in self.parts:
      if part.part_number == part_number:
        return part.field_name
    return str(part_number)
  
  def select(self, argument_definitions):
    variables = filter(lambda x: x.argument_type == 'VAR', argument_definitions)
    var_pairs = list(map(lambda x: f"{self.part_name(x.argument_number)} as {x.value}", variables))
    return f"select {','.join(var_pairs)}"
  
  def froms(self):
    if self.table_name is not None:
      yield f"(select * from {self.table_name})"
    for rule in self.rules:
      yield f"({rule.to_sql()})"

  def filter(self, argument_definitions):
    constants = filter(lambda x: x.argument_type == 'CONST', argument_definitions)
    const_pairs = list(map(lambda x: f"{self.part_name(x.argument_number)} = '{x.value}'", constants))
    return f"{' and '.join(const_pairs)}"

  # this should run it against the db.
  def query(self, argument_definitions):
    if self.query_hook is not None:
      return self.query_hook(self, argument_definitions)
    else:
      return self.db.data_query(self.query_sql(argument_definitions))
  
  def insert_sql(self, values) -> str:
    return f"insert into {self.table_name} ({', '.join([p.field_name for p in self.parts])}) values ({', '.join([_quote(v) for v in values])})"
    
  def query_sql(self, argument_definitions):
    return f"{self.select(argument_definitions)} from {'union'.join(self.froms())} where {self.filter(argument_definitions)}"

  def declare(self, argument_definitions):
    if len(self.fact_hooks) > 0:
      return all([hook(self, argument_definitions) for hook in self.fact_hooks])
    elif self.table_name is None:
      raise Exception(f"Predicate {self.name}/{self.arity} is not a table")
    else:
      return self.insert_sql([a.value for a in argument_definitions])

class PredicatePart:
  table_name = "predicate_parts"
  fields = ["predicate_part_id", "predicate_id", "part_number", "field_name"]
  def __init__(self, predicate_part_id, predicate_id, part_number, field_name):
    self.predicate_id = predicate_id
    self.predicate_part_id = predicate_part_id
    self.predicate = None
    self.part_number = part_number
    self.field_name = field_name

class ArgumentDefintion:
  def __init__(self, value):
    self.argument_type = "VAR" if value == value.upper() else "CONST"
    self.value = value

class FactDefinition:
  def __init__(self, predicate_name, arguments):
    self.predicate_name = predicate_name
    self.arguments = [ArgumentDefintion(a) for a in arguments]

  @classmethod
  def from_list(cls, lst):
    return cls(lst[0], lst[1:])

class RuleDefinition:
  def __init__(self, predicate_name: str, arguments: [str], queries: [FactDefinition]):
    self.predicate_name = predicate_name
    self.arguments = [ArgumentDefintion(a) for a in arguments]
    self.queries = queries

  @classmethod
  def from_list(cls, lst):
    return cls(lst[0], lst[1:-1], [FactDefinition.from_list(l) for l in lst[-1]])

class PredicateHook:
  def __init__(self, predicate_name, arity, action):
    self.predicate_name = predicate_name
    self.arity = arity
    self.action = action
    
class CustomPredicate:
  def __ini__(self, predicate_name, arguments, query_hook=None, fact_hooks=[]):
    self.predicate_name = predicate_name
    self.arity = len(arguments)
    self.action = self.action

class LogicDB:
  def __init__(self, file_name):
    self.file_name = file_name
    self.predicates = {}
    self.predicate_parts = {}
    self.rules = {}
    self.rule_arguments = {}
    self.queries = {}
    self.query_arguments = {}
    self.create()
    self.load()
    self._new_id_dict = {}
  
  def execute(self, sql):
    conn = sqlite3.connect(self.file_name)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS predicates
                 (name TEXT, arity INTEGER, PRIMARY KEY (name))''')
    conn.commit()
    conn.close()

  def data_query(self, sql, action=None):
    conn = sqlite3.connect(self.file_name)
    conn.row_factory = _dict_factory
    c = conn.cursor()
    rows = c.execute(sql)
    for row in rows:
      if action is not None:
        yield action(**row)
      else:
        yield row
    c.close()
    conn.close()

  def class_query(self, cls):
    return self.data_query(f"SELECT {','.join(cls.fields)} FROM {cls.table_name}", cls)

  def run(self, lst):
    
    if isinstance(lst[-1], list):
      r = RuleDefinition.from_list(lst)
      self.add_rule(r)
    else:
      f = FactDefinition.from_list(lst)
      if all(map(lambda x: x.argument_type == "CONST", f.arguments)):
        return self.add_fact(f)
      else:
        return self.query(f)
  
  def find_predicate(self, name, arity):
    for predicate in self.predicates.values():
      if predicate.name == name and predicate.arity == arity:
        return predicate
    return None

  def add_fact(self, fact_definition):
    predicate = self.find_predicate(fact_definition.predicate_name, len(fact_definition.arguments))
    if predicate is None or predicate.table_name is None:
      raise Exception(f"Predicate {fact_definition.predicate_name}/{len(fact_definition.arguments)} not found")
    sql = predicate.insert([a.value for a in fact_definition.arguments])
    self.execute(sql)

  def add_rule(self, rule_definition):
    predicate = self.find_predicate(rule_definition.predicate_name, len(rule_definition.arguments))
    if predicate is None:
      raise Exception(f"Predicate {rule_definition.predicate_name}/{len(rule_definition.arguments)} not found")
    raise Exception("Not implemented")
  
  def create_predicate(self, name, arity, table_name, fields_with_types): 
    if table_name != None:
      cts = f"create table {table_name} ({','.join([f'{fft[0]} {fft[1]}' for fft in fields_with_types])})"
      self.execute(cts)

      self.execute("""insert into predicates (name, arity, table_name) 
                  values (:name, :arity, :table_name)""", 
                  **{"name":name, "arity":arity, "table_name":table_name})
    
    for i, field_with_type in enumerate(fields_with_types):
      field, field_type = field_with_type
      self.execute("""insert into predicate_parts 
                      (predicate_id
                      ,seq
                     ,field_name
                     ,field_type)
                   select id, :seq, :field_name, :field_type
                   from predicate 
                   where name = :predicate_name and arity = :arity
                 """, 
                 **{"predicate_name":name
                    ,"arity":arity
                    ,"seq":i
                    ,"field_name":field
                    ,"field_type":field_type})

  def _new_id(self, type_name):
    new_id = self._new_id.get(type_name, -1)
    new_id = new_id - 1
    self._new_id[type_name] = new_id
    return new_id

  def register(self, custom: CustomPredicate):
    predicate = Predicate(custom.predicate_name, custom.arity, None)
    predicate.query_hook = custom.query_hook
    predicate.fact_hooks = custom.fact_hooks
    predicate.predicate_id = self._new_id("predicate")
    predicate.attach(self)
    self.predicates[predicate.predicate_id] = predicate
    for i, argument in enumerate(custom.arguments):
      part = PredicatePart(self._new_id("predicate_part"), predicate.predicate_id, i, argument)
      part.attach(self)
      self.predicate_parts[part.predicate_part_id] = part
    return predicate

  def query(self,  fact_definition):
    predicate = self.find_predicate(fact_definition.predicate_name, len(fact_definition.arguments))
    if predicate is None:
      raise Exception(f"Predicate {fact_definition.predicate_name}/{len(fact_definition.arguments)} not found")
    sql = predicate.query(fact_definition.arguments)
    return self.data_query(sql)
    
  def create(self):
    self.create_predicate("predicate", 
                          3, 
                          "predicate", 
                          [
                            ("id", "INTEGER AUTOINCREMENT PRIMARYKEY"), 
                            ("name", "TEXT"), 
                            ("arity", "INTEGER"),
                            ("table_name", "TEXT")
                          ])
    self.create_predicate("predicate_part",
                          4,
                          "predicate_part",
                          [
                            ("id", "INTEGER AUTOINCREMENT PRIMARYKEY"),
                            ("predicate_id", "INTEGER"),
                            ("seq", "INTEGER"),
                            ("field_name", "TEXT"),
                            ("field_type", "TEXT")
                          ])
    self.create_predicate("rule",
                          2,
                          "rule",
                          [
                            ("id", "INTEGER AUTOINCREMENT PRIMARYKEY"),
                            ("predicate_id", "INTEGER")
                          ])
    self.create_predicate("rule_argument",
                          4,
                          "rule_argument",
                          [
                            ("id", "INTEGER AUTOINCREMENT PRIMARYKEY"),
                            ("rule_id", "INTEGER"),
                            ("seq", "INTEGER"),
                            ("argument", "TEXT"),
                            ("argument_type", "TEXT")
                          ])
    self.create_predicate("query",
                          4,
                          "query",
                          [
                            ("id", "INTEGER AUTOINCREMENT PRIMARYKEY"),
                            ("rule_id", "INTEGER"),
                            ("seq", "INTEGER"),
                            ("predicate_id", "INTEGER")
                          ])
    self.create_predicate("query_argument",
                          4,
                          "query_argument",
                          [
                            ("id", "INTEGER AUTOINCREMENT PRIMARYKEY"),
                            ("query_id", "INTEGER"),
                            ("seq", "INTEGER"),
                            ("argument", "TEXT"),
                            ("argument_type", "TEXT")
                          ])
    self.create_predicate("link",
                          5,
                          "link",
                          [
                            ("id", "INTEGER AUTOINCREMENT PRIMARYKEY"),
                            ("link_name", "TEXT"),
                            ("local_part_id", "INTEGER"),
                            ("remote_part_id", "INTEGER"),
                            ("seq", "INTEGER")
                          ])
                          
  def create_link(self, name, local_and_remotes):
    for index, pair in enumerate(local_and_remotes):
      local, remote = pair
      self.execute("""insert into link (link_name, local_part_id, remote_part_id)
                      select l.id, r.id
                      from predicate_part l, predicate_part r
                      where l.predicate_id = :local_predicate_id
                      and l.seq = :local_seq
                      and r.predicate_id = :remote_predicate_id
                      and r.seq = :remote_seq
                      """,
                      **{"local_predicate_id":local.predicate_id
                        ,"local_seq":local.seq
                        ,"remote_predicate_id":remote.predicate_id
                        ,"remote_seq":remote.seq
                        })                   
                          
  def load(self):
    classes = [Predicate, PredicatePart, Rule, RuleArgument, Query, QueryArgument]
    for cls in classes:
      for row in self.class_query(cls):
        row.attach(self)

taush._environ_["ldb"] = LogicDB("logic.db")
taush._environ_["lisp"] = taush.taush._environ_["lisp"] | {
  "!": lambda *args: taush._environ_["ldb"].run(list(args)),
  "predicate": lambda *args: taush._environ_["ldb"].create_predicate(*args),
}

