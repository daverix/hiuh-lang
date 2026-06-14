class Environment:

    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def define(self, name, value):
        self.vars[name] = value

    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        return name

    def get_local_bindings(self):
        """Returns a dict of variables defined in this environment only (not parent)."""
        return {k: v for k, v in self.vars.items() if not k.startswith('_')}