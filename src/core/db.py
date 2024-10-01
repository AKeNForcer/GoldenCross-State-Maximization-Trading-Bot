from pymongo.database import Database
from datetime import datetime



class DatabaseWrapper:
    def __init__(self, db: Database, module_name: str) -> None:
        self.db = db
        self.module_name = module_name
    
    def __getitem__(self, path: str):
        return self.db[f'{self.module_name}-{path}']





class KeyRef:
    def __init__(self, path=None, keys: list[str] | str = None, apply=None):
        if keys is str:
            keys = [keys]
        if keys is None:
            keys = []
        self.keys = keys
        self.path = path
        self._apply = apply
    
    def __getitem__(self, key):
        return KeyRef(self.path, self.keys + [key])
    
    def __repr__(self):
        s = f"<KeyRef {self.path or '.'}>" + ''.join([ '.' + k for k in self.keys ])
        if self._apply:
            return f"{self._apply}({s})"
        return s
    
    def apply(self, apply):
        return KeyRef(self.path, self.keys, apply)





class State:
    def __init__(self, db: Database | None = None,
                 initial_paths: list[str] = None,
                 parent=None, name: str | None = None,
                 require_db=False):
        self.db = db
        self.name = name
        self.parent: State | None = parent
        self.require_db = require_db

        self.store: dict[str, dict | None] = {}
        self.children: dict[str, State] = {}

        if parent is None:
            self.abs_path = '/'
        else:
            if name is None:
                raise ValueError('SubState require name')
            self.abs_path = self.parent.abs_path + self.name + '/'
            
        
        self._validate_db()
        self.load(initial_paths)
    

    def _validate_db(self):
        if not self.require_db:
            return
        if self.db is not None:
            return
        raise ValueError('Database is required')


    def _get_self(self, path: str | list = '', inclusive=False):
        if inclusive:
            if type(path) is str:
                path = './' + path
                path = path.split('/')
                path = path[:-1]
                path = '/'.join(path)
            else:
                path = path[:-1]

        if type(path) is str:
            if path in ['.', '']:
                return self
            
            if path[0] == '/':
                if self.parent is None:
                    return self._get_self(path[1:])
                return self.parent._get_self(path)
            
            if path == '..' or path[0:3] == '../':
                return self.parent._get_self(path.lstrip('..').lstrip('/'))
            
            if path[0:2] == './':
                return self._get_self(path.lstrip('./'))
            
            path = path.strip('/').split('/')

        if len(path) == 0:
            return self

        if path[0] not in self.children:
            self.sub_state(path[0],
                           initial_paths=None,
                           require_db=self.require_db)

        return self.children[path[0]]._get_self(path[1:])


    def load(self, paths: list[str] | str | None=None, replace: bool | str=False, create=True):
        if paths is None:
            return
        
        self._validate_db()

        if self.db is None:
            return
        
        if type(paths) != list:
            paths = [paths]
        
        now = datetime.now()
        for path in paths:
            target, path, abs_path = self._get_target_utils(path)

            _res = self.db[abs_path].find().sort("__updated_time__", -1).limit(1)
            res = { '__updated_time__': now } if create else None
            for r in _res:
                res = r
                break
            
            if res is None:
                continue

            if not target.store.get(path):
                target[path] = res
            else:
                if replace == True or replace == 'force':
                    target[path] = res
                if replace == 'new' and \
                    target[path]['__updated_time__'] < res['__updated_time__']:
                    target[path] = res
    

    def _acquire_key_ref(self, value: dict, stack=None):
        stack = stack or []
        key_refs = []

        if type(value) in [dict, list]:
            rm_keys = []

            _value = {**value} if type(value) is dict else [*value]
            for k, v in (value.items() if type(value) is dict else enumerate(value)):
                stack.append(k)
                if type(v) == KeyRef:
                    rm_keys.append(k)
                    key_refs.append([*stack])
                else:
                    _key_refs, v = self._acquire_key_ref(v, stack)
                    _value[k] = v
                    key_refs += _key_refs
                stack.pop()
        
            for r in rm_keys[::-1]:
                del _value[r]
            
            value = _value
        
        return key_refs, value
    

    def _get_target_utils(self, path):
        target = self._get_self(path, inclusive=True)
        path = path.split('/')[-1]
        abs_path = target.abs_path + path

        return target, path, abs_path


    def save(self, key=None, paths: list[str] | None=None, recursive=True):
        if paths is None and recursive:
            for child in self.children.values():
                child.save(key, recursive=True)

        self._validate_db()
        if self.db is None:
            return
        
        key_refs = []
        for path in paths or self.store:
            target, path, abs_path = self._get_target_utils(path)
            _key_refs, value = self._acquire_key_ref(target[path])
            
            key_refs.append((path, _key_refs))

            obj = {}
            obj["__save_from__"] = self.abs_path
            if key is not None:
                obj["__key__"] = key

            col = target.db[abs_path]
            obj = { **obj, **value }
            if '_id' in obj:
                del obj['_id']
            _id = col.insert_one(obj).inserted_id
            target[path]['_id'] = _id
            col.create_index([("__updated_time__", -1)])
        
        
        for path, stacks in key_refs:
            target, path, abs_path = self._get_target_utils(path)
            target_obj = target[path]

            for stack in stacks:
                t = target_obj
                for s in stack[:-1]:
                    t = t[s]
                # print(t)
                key_ref = t[stack[-1]]

                _target, _path, _ = \
                    self._get_target_utils(key_ref.path or path)
                
                val = _target[_path]
                for k in key_ref.keys:
                    val = val[k]
                if key_ref._apply:
                    val = key_ref._apply(val)
                t[stack[-1]] = val

            target_obj = {**target_obj}
            _id = target_obj['_id']
            del target_obj['_id']

            col.update_one({ '_id': _id },
                           { '$set': target_obj })
            
            
    def sub_state(self, name: str | None = None,
                  initial_paths: list[str] = None,
                  require_db=False):
        name = name.strip('/').split('/')
        
        if name[0] not in self.children:
            sub_state = State(initial_paths=None,
                              name=name[0],
                              require_db=require_db,
                              db=self.db,
                              parent=self)
            self.children[name[0]] = sub_state
        else:
            sub_state = self.children[name[0]]
        
        if len(name) > 1:
            return sub_state.sub_state('/'.join(name[1:]),
                                       initial_paths=initial_paths,
                                       require_db=require_db)
        
        sub_state.load(initial_paths)

        return sub_state
    

    def __contains__(self, path: str):
        target = self._get_self(path, inclusive=True)
        if target != self:
            return path.split('/')[-1] in target
        
        if path not in self.store:
            self.load(path, create=False)
        return path in self.store


    def __getitem__(self, path: str):
        target = self._get_self(path, inclusive=True)
        if target != self:
            return target[path.split('/')[-1]]

        if path not in self.store:
            self.load(path, create=False)
        if path not in self.store:
            raise KeyError(f'{self.abs_path} + {path}')
        return self.store[path]
    

    def __setitem__(self, path: str, value: dict):
        target = self._get_self(path, inclusive=True)
        if target != self:
            target[path.split('/')[-1]] = value
            return
        
        if type(value) != dict:
            raise ValueError('value is not a dict')
        self.store[path] = { '__updated_time__': datetime.now(), **value}
        

    def __delitem__(self, path: str):
        target = self._get_self(path, inclusive=True)
        if target != self:
            del target[path.split('/')[-1]]
            return
        
        abs_path = self.abs_path + path
        if self.db is not None:
            self.db[abs_path].drop()
        del self.store[path]

    
    def ls(self):
        return self.store.keys()
    
    
    def ls_children(self):
        return self.children.keys()






class StateInjectable:
    def __init__(self, state: State | None = None) -> None:
        self.state = state
    
    def inject_state(self, state: State):
        self.state = state
