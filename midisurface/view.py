class ViewSet:
    def __init__(self, controller):
        self.controller = controller
        self.view_stack = []

    def render(self):
        if self.view_stack:
            self.view_stack[-1].render(self.controller)
        else:
            self.controller.reset()

    def push(self, view):
        self.view_stack.append(view)
        self.render()

    def pop(self, view=None):
        while self.view_stack:
            if view is None:
                self.view_stack.pop()
                self.render()
                return
            else:
                if self.view_stack and self.view_stack[-1] is view:
                    self.render()
                    return
                self.view_stack.pop()
        self.render()

    def dispatch(self):
        for group, control, value in self.controller.get_messages():
            if self.view_stack:
                self.view_stack[-1].dispatch(self.controller, group, control, value)

    def run(self):
        while True:
            self.dispatch()


class View:
    def __init__(self, name, *controls):
        self.name = name
        self.controls = controls

    def dispatch(self, controller, group, control, value):
        for ctrl_instance in self.controls:
            ctrl_instance.dispatch(controller, group, control, value)

    def render(self, controller):
        for ctrl_instance in self.controls:
            ctrl_instance.render(controller)