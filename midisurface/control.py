import uuid
import math


O_FIRST = -1000000
O_LAST = 1000000


class ControlSet(list):
    def test(self, group, control):
        for res in self:
            if isinstance(res, ControlSet):
                return res.test(group, control)
            t_group, t_control = res
            if t_group is None or t_group == group:
                if t_control is None or t_control == control:
                    return True
        return False

    def all(self, controller):
        grouped = {}
        for group, control in controller._BTN_MAP.values():
            grouped.setdefault(group, []).append(control)
        for res in self:
            if isinstance(res, ControlSet):
                yield from res
                continue
            group, control = res
            if group is None:
                for k in grouped:
                    if control is None:
                        for v in grouped[k]:
                            yield k, v
                    else:
                        if control in grouped[k]:
                            yield k, control
            elif control is None:
                if group in grouped:
                    for v in grouped[group]:
                        yield group, v
            else:
                yield group, control
        # TODO: when group is grid and control is None, yield all of those too


class GridControlSet(ControlSet):
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2

    def test(self, group, control):
        if group != 'GRID':
            return False
        x, y = control
        return x >= self.x1 and y >= self.y1 and x <= self.x2 and y <= self.y2

    def all(self, controller):
        for y in range(self.y1, self.y2 + 1):
            for x in range(self.x1, self.x2 + 1):
                yield 'GRID', (x, y)


class Control:
    STORE_BY_ID = False

    def __init__(self, name, controls, events=None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.controls = controls
        self.events = {}
        self.last_state = {}

        for ev, callbacks in (events or {}).items():
            try:
                iter(callbacks)
            except TypeError:
                callbacks = [callbacks]

            for cb in callbacks:
                try:
                    cb, order = cb
                except (TypeError, ValueError):
                    order = 0

                self.on(ev, cb, order)

    def _process_value(self, controller, group, control, value):
        return value

    def dispatch(self, controller, group, control, value):
        if self.controls.test(group, control):
            value = self._process_value(controller, group, control, value)
            value_key = self.id if self.STORE_BY_ID else (group, control)
            last_state = self.last_state.get(value_key)
            self._emit(controller, self, 'raw', group, control, value)
            if value and not last_state:
                self._emit(controller, self, 'press', group, control)
            elif not value and last_state:
                self._emit(controller, self, 'release', group, control)
            if value != last_state:
                self._emit(controller, self, 'change', group, control, last_state, value)
            if last_state is not None:
                if value > last_state:
                    self._emit(controller, self, 'up', group, control, last_state, value)
                elif value < last_state:
                    self._emit(controller, self, 'down', group, control, last_state, value)
            self.last_state[value_key] = value

    def render(self, controller):
        pass

    def on(self, event, callback, order=0):
        id = event + ':' + str(uuid.uuid4())
        self.events.setdefault(event, {})[id] = (order, callback)
        return id

    def off(self, id):
        event, id = ':'.split(id)
        if event in self.events and id in self.events[event]:
            del self.events[event][id]

    def _emit(self, controller, ctrl_instance, event, group, control, *args):
        for _, cb in sorted(self.events.get(event, {}).values(), key=lambda v: v[0]):
            try:
                cb(controller, ctrl_instance, event, group, control, *args)
            except:
                # TODO: log
                pass


class Momentary(Control):
    def __init__(self, name, controls, on_color='on', off_color='off', **kwargs):
        super().__init__(name, controls, **kwargs)
        self.on_color = on_color
        self.off_color = off_color
        self.on('press', self._set_color, O_FIRST)
        self.on('release', self._set_color, O_FIRST)

    def render(self, controller):
        for group, control in self.controls.all(controller):
            controller.set_color(group, control, self.off_color)

    def _set_color(self, controller, ctrl_instance, event, group, control):
        if event == 'press':
            controller.set_color(group, control, self.on_color)
        else:
            controller.set_color(group, control, self.off_color)


class Toggle(Control):
    def __init__(self, name, controls, states=2, colors=['off', 'on'], **kwargs):
        if len(colors) != states:
            raise ValueError("Number of colors must match number of states")
        super().__init__(name, controls, **kwargs)
        self.states = states
        self.colors = colors
        self.on('press', self._handle_control, O_FIRST)
        self.c_last_state = {}

    def render(self, controller):
        for group, control in self.controls.all(controller):
            controller.set_color(group, control, self.colors[self.c_last_state.get((group, control), 0)])

    def _handle_control(self, controller, ctrl_instance, event, group, control):
        self.c_last_state.setdefault((group, control), 0)
        self.c_last_state[(group, control)] += 1
        if self.c_last_state[(group, control)] == self.states:
            self.c_last_state[(group, control)] = 0
        controller.set_color(group, control, self.colors[self.c_last_state.get((group, control), 0)])
        self._emit(controller, self, 'toggle', group, control, self.c_last_state[(group, control)])


class Radio(Control):
    def __init__(self, name, controls, on_color='on', off_color='off', select_first=True, allow_deselect=False, **kwargs):
        super().__init__(name, controls, **kwargs)
        self.on_color = on_color
        self.off_color = off_color
        self.select_first = select_first
        self.allow_deselect = allow_deselect
        self.first_selected = False
        self.selected = None
        self.on('press', self._handle_control, O_FIRST)

    def render(self, controller):
        if self.select_first and not self.first_selected:
            try:
                self.selected = next(self.controls.all(controller))
                self.first_selected = True
            except StopIteration:
                pass

        for group, control in self.controls.all(controller):
            controller.set_color(group, control, self.on_color if (group, control) == self.selected else self.off_color)

    def _handle_control(self, controller, ctrl_instance, event, group, control):
        if (group, control) == self.selected:
            if self.allow_deselect:
                prev = self.selected
                self.selected = None
                self.render(controller)
                self._emit(controller, self, 'radio', group, control, prev, None)
        else:
            prev = self.selected
            self.selected = (group, control)
            self.render(controller)
            self._emit(controller, self, 'radio', group, control, prev, self.selected)


class Fader(Control):
    def __init__(self, name, controls, **kwargs):
        super().__init__(name, controls, **kwargs)
        self.on('raw', self._handle_control, O_FIRST)

    def _handle_control(self, controller, ctrl_instance, event, group, control, value):
        if value == 0:
            self._emit(controller, self, 'min', group, control)
        elif value == 127:
            self._emit(controller, self, 'max', group, control)


class VirtualFader(Control):
    STORE_BY_ID = True

    def __init__(self, name, controls, colors=None, group_colors=False, **kwargs):
        super().__init__(name, controls, **kwargs)
        self.raw_colors = colors or ['on']
        self.colors = None
        self.group_colors = group_colors
        self.control_pos = None
        self.value = 0
        self.has_changed = False
        self.on('raw', self._handle_control, O_FIRST)

    def render(self, controller):
        if self.control_pos is None:
            self.control_pos = list(reversed(list(self.controls.all(controller))))
        if self.colors is None:
            per_group = math.ceil(len(self.control_pos) / len(self.raw_colors))
            self.colors = []
            for c in self.raw_colors:
                for _ in range(per_group):
                    self.colors.append(c)

        for idx, (group, control) in enumerate(self.control_pos):
            if idx <= self.value:
                if self.group_colors:
                    c = self.colors[idx]
                else:
                    c = self.colors[self.value]
                controller.set_color(group, control, c)
            else:
                controller.set_color(group, control, 'off')

    def _process_value(self, controller, group, control, value):
        if value:
            new_value = self.control_pos.index((group, control))
            self.has_changed = (self.value != new_value)
            self.value = new_value
            self.render(controller)
        return int((self.value / 7) * 127)

    def _handle_control(self, controller, ctrl_instance, event, group, control, value):
        if self.has_changed:
            self.has_changed = False
            if value == 0:
                self._emit(controller, self, 'min', group, control)
            elif value == 127:
                self._emit(controller, self, 'max', group, control)
