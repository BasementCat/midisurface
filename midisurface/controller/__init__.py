import mido


class ControllerError(Exception):
    pass


class ControllerNotFound(ControllerError):
    pass


class MultipleControllersFound(ControllerError):
    pass


class Color:
    def __init__(self, rgb=None, name=None, flash=None, fade=None, intensity=None):
        self.rgb = rgb
        self.name = name
        self.flash = flash
        self.fade = fade
        self.intensity = intensity

    def __str__(self):
        out = 'Color('
        if self.rgb:
            out += '#{:02x}{:02x}{:02x}'.format(*self.rgb)
        else:
            out += self.name
            if self.intensity is not None:
                out += '@' + str(self.intensity)
        out += ', flash=' + str(self.flash) + ', fade=' + str(self.fade) + ')'
        return out


class ControllerBase:
    PORT_NAME = None
    HAS_FEEDBACK = False
    HAS_RGB = False
    HAS_GRID = False

    def __init__(self, port_number=None):
        ports = set(mido.get_input_names())
        if self.HAS_FEEDBACK:
            ports &= set(mido.get_output_names())

        f_ports = list(sorted(filter(lambda p: p.startswith(self.PORT_NAME), ports)))
        if not f_ports:
            raise ControllerNotFound(f"No controller named '{self.PORT_NAME}' was found (found {ports})")
        if len(f_ports) > 1 and port_number is None:
            raise MultipleControllersFound(f"Multiple controllers named '{self.PORT_NAME}' were found, the port number is required")

        self.port = getattr(mido, 'open_ioport' if self.HAS_FEEDBACK else 'open_input')(f_ports[port_number or 0])

    def _interpret_color(self, color):
        out = None
        for chunk in map(str.strip, color.split(';')):
            col, flags = map(str.strip, (chunk + ' ').split(' ', 1))
            flags = set(map(str.strip, flags.split(' ')))
            intensity = None
            convert_rgb_range = False
            if col.startswith('#'):
                name = None
                rgb = (
                    int(col[1:3], 16),
                    int(col[3:5], 16),
                    int(col[5:7], 16),
                )
                # Assume range is 0-255, and convert
                convert_rgb_range = True
            elif ',' in col:
                name = None
                rgb = tuple(map(int, map(str.strip, col.split(','))))
                convert_rgb_range = any(map(lambda v: v > 127, rgb))
            else:
                name = col
                rgb = None
                if '@' in name:
                    name, intensity = name.split('@', 1)
                    intensity = int(intensity)

            if convert_rgb_range:
                rgb = tuple(map(lambda v: int((v / 255) * 127), rgb))

            flags = {
                'flash': ('flash' in flags),
                'fade': ('fade' in flags),
            }

            if out:
                out.flash = Color(rgb, name, intensity=intensity, **flags)
                return out
            else:
                out = Color(rgb, name, intensity=intensity, **flags)
        return out


    def get_messages(self):
        for msg in self.port.iter_pending():
            res = self._process_control(msg)
            if res:
                yield res

    def send(self, type_, **kwargs):
        return self.port.send(mido.Message(type_, **kwargs))

    def reset(self, *groups):
        btns = []
        if groups:
            for g, c in self._BTN_MAP.values():
                if g in groups:
                    btns.append((g, c))
            if 'GRID' in groups and self.HAS_GRID:
                w, h = self._GRID_SIZE
                for y in range(h):
                    for x in range(w):
                        btns.append(('GRID', (x, y)))
        else:
            btns = list(self._BTN_MAP.values())
            if self.HAS_GRID:
                w, h = self._GRID_SIZE
                for y in range(h):
                    for x in range(w):
                        btns.append(('GRID', (x, y)))
        for g, c in btns:
            try:
                self.set_color(g, c, 'off')
            except:
                pass
