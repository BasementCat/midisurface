from . import ControllerBase


class APCMini(ControllerBase):
    PORT_NAME = 'APC MINI'
    HAS_FEEDBACK = True
    HAS_GRID = True

    _BTN_MAP = {
        82: ('RIGHT', 'CLIP_STOP'),
        83: ('RIGHT', 'SOLO'),
        84: ('RIGHT', 'REC_ARM'),
        85: ('RIGHT', 'MUTE'),
        86: ('RIGHT', 'SELECT'),
        87: ('RIGHT', '1'),
        88: ('RIGHT', '2'),
        89: ('RIGHT', 'STOP_ALL'),

        64: ('NAV', 'UP'),
        65: ('NAV', 'DOWN'),
        66: ('NAV', 'LEFT'),
        67: ('NAV', 'RIGHT'),

        68: ('FADER_CTRL', 'VOLUME'),
        69: ('FADER_CTRL', 'PAN'),
        70: ('FADER_CTRL', 'SEND'),
        71: ('FADER_CTRL', 'DEVICE'),

        98: ('SHIFT', 'SHIFT'),
    }
    _BTN_MAP_INV = dict(map(reversed, _BTN_MAP.items()))
    _GRID_SIZE = (8, 8)

    _COL_MAP = {
        ('off', False): 0,
        ('off', True): 0,
        ('on', False): 1,
        ('on', True): 2,
        ('green', False): 1,
        ('green', True): 2,
        ('red', False): 3,
        ('red', True): 4,
        ('yellow', False): 5,
        ('yellow', True): 6,
    }

    def _process_control(self, msg):
        if msg.type in ('note_on', 'note_off'):
            value = (True if msg.type == 'note_on' else False)
            if msg.note < 64:
                y, x = divmod(msg.note, 8)
                y = 7 - y
                return 'GRID', (x, y), value
            else:
                return tuple(list(self._BTN_MAP[msg.note]) + [value])
        elif msg.type == 'control_change':
            return 'FADER', msg.control - 48, msg.value

    def _interpret_color(self, color):
        color = super()._interpret_color(color)
        if color.rgb:
            raise ValueError("No RGB support")
        if color.fade:
            raise ValueError("No fade support")
        if (color.name, bool(color.flash)) not in self._COL_MAP:
            raise ValueError("Invalid color: " + str(color))
        return color

    def set_color(self, group, control, color):
        color = self._interpret_color(color)
        if group == 'SHIFT':
            return
        elif group == 'GRID':
            self.send('note_on', note=((7 - control[1]) * 8) + control[0], velocity=self._COL_MAP[(color.name, bool(color.flash))])
        elif group in ('RIGHT', 'NAV', 'FADER_CTRL'):
            self.send('note_on', note=self._BTN_MAP_INV[(group, control)], velocity=0 if color.name == 'off' else 1)
        else:
            raise ValueError("Invalid group")