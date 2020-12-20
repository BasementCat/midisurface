from . import ControllerBase


class LaunchpadMK2(ControllerBase):
    PORT_NAME = 'Launchpad MK2'
    HAS_FEEDBACK = True
    HAS_GRID = True
    HAS_RGB = True

    _BTN_MAP = {
        104: ('NAV', 'UP'),
        105: ('NAV', 'DOWN'),
        106: ('NAV', 'LEFT'),
        107: ('NAV', 'RIGHT'),

        108: ('MODE', 'SESSION'),
        109: ('MODE', 'USER1'),
        110: ('MODE', 'USER2'),
        111: ('MODE', 'MIXER'),

        89: ('RIGHT', 'VOLUME'),
        79: ('RIGHT', 'PAN'),
        69: ('RIGHT', 'SENDA'),
        59: ('RIGHT', 'SENDB'),
        49: ('RIGHT', 'STOP'),
        39: ('RIGHT', 'MUTE'),
        29: ('RIGHT', 'SOLO'),
        19: ('RIGHT', 'RECORDARM'),
    }
    _BTN_MAP_INV = dict(map(reversed, _BTN_MAP.items()))

    _GRID_SIZE = (8, 8)

    _COL_MAP = {
        'off': (0, 1, True),
        'on': (20, 4, True),  # green
        'white': (1, 3, False),  # offset, count, invert
        'red': (4, 4, True),
        'orange': (8, 4, True),
        'yellow': (12, 4, True),
        'forest': (16, 4, True),
        'green': (20, 4, True),
        'lime': (24, 4, True),
        'cyan1':  (28, 4, True),
        'cyan2':  (32, 4, True),
        'ltblue': (36, 4, True),
        'mdblue': (40, 4, True),
        'blue': (44, 4, True),
        'purple': (48, 4, True),
        'ltpink': (52, 4, True),
        'pink': (56, 4, True),
    }

    def _process_control(self, msg):
        if msg.type == 'control_change':
            group, control = self._BTN_MAP[msg.control]
            return group, control, msg.value
        else:
            if msg.note in self._BTN_MAP:
                group, control = self._BTN_MAP[msg.note]
                return group, control, msg.velocity
            x = int((msg.note - 11) % 10)
            y = 7 - int((msg.note - 11) / 10)
            return 'GRID', (x, y), msg.velocity

    def _send_color_basic(self, x, y, channel, index):
        if x == 'GRID':
            x, y = y
            note =int(11 + (((7 - y) * 10) + x))
            self.send('note_on', channel=channel, note=note, velocity=index)
        elif x in ('NAV', 'MODE'):
            button = self._BTN_MAP_INV[(x, y)]
            self.send('control_change', channel=channel, control=button, value=index)
        elif x == 'RIGHT':
            button = self._BTN_MAP_INV[(x, y)]
            self.send('note_on', channel=channel, note=button, velocity=index)

    def _get_color_index(self, color, intensity=None):
        intensity = 4 if intensity is None else intensity
        offset, count, invert = self._COL_MAP[color]
        intensities = list(map(int, range(offset, offset + count)))
        if invert:
            intensities = list(reversed(intensities))
        intensities[0], intensities[-1] = intensities[-1], intensities[0]
        return intensities[min(len(intensities) - 1, intensity - 1)]

    def _set_color_basic(self, x, y, color):
        index = self._get_color_index(color.name, color.intensity)
        flash_index = None
        if color.flash and color.flash is not True:
            flash_index = self._get_color_index(color.flash.name, color.flash.intensity)

        if color.flash:
            if flash_index is not None:
                self._send_color_basic(x, y, 0, index)
                self._send_color_basic(x, y, 1, flash_index)
            else:
                self._send_color_basic(x, y, 1, index)
        elif color.fade:
            self._send_color_basic(x, y, 2, index)
        else:
            self._send_color_basic(x, y, 0, index)

    def _set_color_rgb(self, x, y, color):
        r, g, b = color.rgb
        if x == 'GRID':
            x, y = y
            button = int(11 + (((7 - y) * 10) + x))
        else:
            button = self._BTN_MAP_INV[(x, y)]
        self.send('sysex', data=[0, 32, 41,  2, 24, 11, button, r, g, b])

    def _interpret_color(self, color):
        color = super()._interpret_color(color)
        if color.rgb and (color.flash or color.fade):
            raise ValueError("Can't flash/fade w/ rgb color")
        if color.name and color.name not in self._COL_MAP:
            raise ValueError("Invalid color: " + str(color))
        if color.flash and color.flash is not True:
            if color.flash.rgb:
                raise ValueError("Can't flash w/ rgb color")
            elif color.flash.name not in self._COL_MAP:
                raise ValueError("Invalid flash color: " + str(color.flash))
        return color

    def set_color(self, group, control, color):
        color = self._interpret_color(color)
        if color.rgb:
            self._set_color_rgb(group, control, color)
        else:
            self._set_color_basic(group, control, color)