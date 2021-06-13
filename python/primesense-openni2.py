#!/usr/bin/python3
import os
import sys
from collections import OrderedDict

from ctypes import c_char

sys.path.append(os.path.join('venv', 'Lib', 'site-packages'))

from primesense import openni2
from primesense._openni2 import ONI_DEVICE_PROPERTY_SERIAL_NUMBER


class Device(openni2.Device):
    _sensor_type_map = {
        'Infrared': 1,
        'Color': 2,
        'Depth': 3,
    }

    _serial_number = None
    _sensor_type_labels = None
    _video_mode_labels = None
    disconnected = False

    @property
    def serial_number(self):
        if self._serial_number is not None:
            return self._serial_number
        else:
            self._serial_number = self._get_serial_number(self)
            return self._serial_number

    @staticmethod
    def _get_serial_number(device):
        return device.get_property(ONI_DEVICE_PROPERTY_SERIAL_NUMBER, (c_char * 100)).value.decode('utf-8')

    @staticmethod
    def _get_sensor_type_labels(device):
        return [k for k, v in device._sensor_type_map.items() if device.has_sensor(v)]

    @staticmethod
    def _get_video_mode_labels(device):
        result = dict()
        sensor_labels = [k for k, v in device._sensor_type_map.items() if device.has_sensor(v)]
        for sensor_label in sensor_labels:
            video_modes = device.get_sensor_info(device._sensor_type_map[sensor_label]).videoModes

            result[sensor_label] = dict()
            for video_mode in video_modes:
                fps_label = '{} fps'.format(video_mode.fps)
                resolution_label = '{} x {}'.format(video_mode.resolutionX, video_mode.resolutionY)
                format_label = video_mode.pixelFormat._values_[video_mode.pixelFormat.value] \
                    .replace('ONI_PIXEL_FORMAT_', '') \
                    .replace('_', ' ')
                if fps_label not in result[sensor_label]:
                    result[sensor_label][fps_label] = dict()
                if resolution_label not in result[sensor_label][fps_label]:
                    result[sensor_label][fps_label][resolution_label] = dict()
                if format_label not in result[sensor_label][fps_label][resolution_label]:
                    result[sensor_label][fps_label][resolution_label][format_label] = video_mode

        return result

    def __repr__(self):
        return '<Device {}{}>'.format(
            self.__str__(),
            ' (Disconnected)' if self.disconnected else '',
        )

    def __str__(self):
        return '{} {} {}'.format(
            self.device_info.vendor.decode(),
            self.device_info.name.decode(),
            self.serial_number,
        )

    def update_device_details(self):
        self._serial_number = self._get_serial_number(self)
        self._sensor_type_labels = self._get_sensor_type_labels(self)
        self._video_mode_labels = self._get_video_mode_labels(self)

    def reopen(self):
        self._reopen()
        self.update_device_details()

    @property
    def video_modes(self):
        if type(self._video_mode_labels) is not list:
            self._video_mode_labels = self._get_video_mode_labels(self)

        return self._video_mode_labels


class DeviceListener(openni2.DeviceListener):
    owner = None

    def __init__(self, owner=None):
        self.owner = owner
        super().__init__()

    def on_connected(self, devinfo):
        if self.owner is not None:
            self.owner.on_connected(devinfo)

    def on_disconnected(self, devinfo):
        if self.owner is not None:
            self.owner.on_disconnected(devinfo)


class Devices:
    _device_listener = None
    _known_by_uri = None

    def __init__(self):
        self.refresh()
        self._device_listener = DeviceListener(owner=self)

    def refresh(self):
        if type(self._known_by_uri) is not dict:
            self._known_by_uri = dict()
        uris = openni2.Device.enumerate_uris()

        for uri in uris:
            if uri not in self._known_by_uri:
                self._known_by_uri[uri] = Device(uri)

        global parameter_update_required
        parameter_update_required = True

    def on_connected(self, devinfo):
        if devinfo.uri in self._known_by_uri:
            self._known_by_uri[devinfo.uri].disconnected = False
            self._known_by_uri[devinfo.uri].reopen()
        else:
            self._known_by_uri[devinfo.uri] = Device(devinfo.uri)

        print(self._known_by_uri[devinfo.uri], 'connected')

        global parameter_update_required
        parameter_update_required = True

    def on_disconnected(self, devinfo):
        if devinfo.uri in self._known_by_uri:
            self._known_by_uri[devinfo.uri].disconnected = True

        print(self._known_by_uri[devinfo.uri], 'disconnected')

        global parameter_update_required
        parameter_update_required = True

    @property
    def _known_by_label(self):
        # First collect the disconnected devices. Then update/overwrite with connected devices. A device might have
        # changed uri, thus be represented twice in the _known_by_uri dict. A Device instance is linked to a uri,
        # rather than a serial number. The resulting dict from this method will always return the correct Device
        # instance for the physical camera we are looking for.
        results_by_label = {str(v): v for v in self._known_by_uri.values() if v.disconnected}
        results_by_label.update({str(v): v for v in self._known_by_uri.values() if not v.disconnected})

        results = dict()
        keys = sorted(results_by_label)
        for k in keys:
            results[k] = results_by_label[k]

        return results

    def __repr__(self):
        return '<{}>'.format(', '.join(
            [str(v) for v in self._known_by_uri.values() if not v.disconnected]
        ))

    @property
    def known(self):
        return self._known_by_label

    def __getitem__(self, item):
        return list(self._known_by_label.values()).__getitem__(item)


def get_param_values(scriptOp):
    result = dict()

    if scriptOp.par['Sensor'] is not None:
        for k in ['Dlldirectory', 'Active', 'Sensor', 'Image', 'Fps', 'Resolution', 'Pixelformat', 'Mirrorimage']:
            result.update({k: scriptOp.par[k].val})

    return result


def set_param_values(scriptOp, param_values):
    for k, v in param_values.items():
        if v:
            scriptOp.par[k].val = v

    global last_params
    last_params = param_values


def detect_param_change(scriptOp):
    global last_params
    changed = False
    current_params = get_param_values(scriptOp)

    if last_params and last_params != current_params:
        changed = True

    last_params = current_params
    return changed


def initialize_devices(scriptOp):
    if scriptOp.par['Dlldirectory'] and \
            scriptOp.par['Dlldirectory'].val and \
            os.path.exists(scriptOp.par['Dlldirectory'].val):
        openni2.initialize(dll_directories=scriptOp.par.Dlldirectory.val)

        global devices
        if devices is None:
            devices = Devices()
        else:
            devices.refresh()

        return True
    return False


def populate_menus(p, param_values={}):
    # Device menu
    device_param = p['Device']['Sensor']
    device_param['menuNames'] = list()
    device_param['menuLabels'] = list()

    if devices is not None:
        for k, v in devices.known.items():
            device_param['menuNames'].append(k)
            device_param['menuLabels'].append('{}{}'.format(k, ' (Disconnected)' if v.disconnected else ''))

        if 'Sensor' in param_values:
            device_param_val = param_values['Sensor'] \
                if param_values['Sensor'] in device_param['menuNames'] else device_param['menuNames'][0]
            device = devices.known[device_param_val]

            # Sensor menu
            sensor_param = p['Device']['Image']
            sensor_param['menuNames'] = list(device.video_modes)
            sensor_param['menuLabels'] = list(device.video_modes)

            sensor_param_val = param_values['Image'] \
                if param_values['Image'] in sensor_param['menuNames'] else sensor_param['menuNames'][0]

            # Fps menu
            fps_param = p['Device']['Fps']
            fps_param['menuNames'] = list(device.video_modes[sensor_param_val])
            fps_param['menuLabels'] = list(device.video_modes[sensor_param_val])

            fps_param_val = param_values['Fps'] \
                if param_values['Fps'] in fps_param['menuNames'] else fps_param['menuNames'][0]

            # Resolution menu
            resolution_param = p['Device']['Resolution']
            resolution_param['menuNames'] = list(device.video_modes[sensor_param_val][fps_param_val])
            resolution_param['menuLabels'] = list(device.video_modes[sensor_param_val][fps_param_val])

            resolution_param_val = param_values['Resolution'] \
                if param_values['Resolution'] in resolution_param['menuNames'] else resolution_param['menuNames'][0]

            # Pixelformat menu
            pixelformat_param = p['Device']['Pixelformat']
            pixelformat_param['menuNames'] = list(device.video_modes[sensor_param_val][fps_param_val][resolution_param_val])
            pixelformat_param['menuLabels'] = list(
                device.video_modes[sensor_param_val][fps_param_val][resolution_param_val])

            pixelformat_param_val = param_values['Pixelformat'] \
                if param_values['Pixelformat'] in pixelformat_param['menuNames'] else pixelformat_param['menuNames'][0]

            param_values.update({
                'Sensor': device_param_val,
                'Image': sensor_param_val,
                'Fps': fps_param_val,
                'Resolution': resolution_param_val,
                'Pixelformat': pixelformat_param_val,
            })

    return p, param_values


def par_data():
    return OrderedDict({
        'OpenNI': OrderedDict([
            ('Dlldirectory', OrderedDict([
                ('page', 'OpenNI'),
                ('name', 'Dlldirectory'),
                ('style', 'Folder'),
                ('label', 'DLL Directory'),
                ('default', 'Redist'),
                ('startSection', False),
                ('readOnly', False),
            ])),
            ('Reload', OrderedDict([
                ('page', 'OpenNI'),
                ('name', 'Reload'),
                ('style', 'Pulse'),
                ('label', 'Reload'),
                ('default', False),
                ('startSection', False),
                ('readOnly', False),
            ])),
        ]),
        'Device': OrderedDict([
            ('Active', OrderedDict([
                ('page', 'Device'),
                ('name', 'Active'),
                ('style', 'Toggle'),
                ('label', 'Active'),
                ('default', False),
                ('startSection', False),
                ('readOnly', False),
            ])),
            ('Sensor', OrderedDict([
                ('page', 'Device'),
                ('name', 'Sensor'),
                ('style', 'Menu'),
                ('label', 'Sensor'),
                ('menuNames', list()),
                ('menuLabels', list()),
                ('startSection', False),
                ('readOnly', False),
            ])),
            ('Image', OrderedDict([
                ('page', 'Device'),
                ('name', 'Image'),
                ('style', 'Menu'),
                ('label', 'Image'),
                ('menuNames', list()),
                ('menuLabels', list()),
                ('startSection', False),
                ('readOnly', False),
            ])),
            ('Fps', OrderedDict([
                ('page', 'Device'),
                ('name', 'Fps'),
                ('style', 'Menu'),
                ('label', 'FPS'),
                ('menuNames', list()),
                ('menuLabels', list()),
                ('startSection', False),
                ('readOnly', False),
            ])),
            ('Resolution', OrderedDict([
                ('page', 'Device'),
                ('name', 'Resolution'),
                ('style', 'Menu'),
                ('label', 'Resolution'),
                ('menuNames', list()),
                ('menuLabels', list()),
                ('startSection', False),
                ('readOnly', False),
            ])),
            ('Pixelformat', OrderedDict([
                ('page', 'Device'),
                ('name', 'Pixelformat'),
                ('style', 'Menu'),
                ('label', 'Pixel Format'),
                ('menuNames', list()),
                ('menuLabels', list()),
                ('value', 'bar'),
                ('startSection', False),
                ('readOnly', False),
            ])),
            ('Mirrorimage', OrderedDict([
                ('page', 'Device'),
                ('name', 'Mirrorimage'),
                ('style', 'Toggle'),
                ('label', 'Mirror Image'),
                ('default', False),
                ('startSection', False),
                ('readOnly', False),
            ])),
        ]),
    })


def setup_parameters(scriptOp):
    TDJSON = op.TDModules.mod.TDJSON
    parData = par_data()
    parData, _ = populate_menus(parData)
    TDJSON.addParametersFromJSONOp(scriptOp, parData, destroyOthers=True)


def update_parameters(scriptOp):
    param_values = get_param_values(scriptOp)
    TDJSON = op.TDModules.mod.TDJSON
    parData = par_data()
    parData, param_values = populate_menus(parData, param_values)
    TDJSON.addParametersFromJSONOp(scriptOp, parData, destroyOthers=True)
    if param_values:
        set_param_values(scriptOp, param_values)


def onSetupParameters(scriptOp):
    setup_parameters(scriptOp)


def onPulse(par):
    scriptOp = par.owner
    if par.name == 'Reload':
        if initialize_devices(scriptOp):
            global parameter_update_required
            parameter_update_required = True

    return


def onCook(scriptOp):
    if devices is None:
        initialize_devices(scriptOp)

    # Update parameter when neccessary
    global parameter_update_required
    if detect_param_change(scriptOp):
        parameter_update_required = True
    if parameter_update_required:
        update_parameters(scriptOp)
        parameter_update_required = False

    return


# Executes inside of TouchDesigner. __name__ will contain name of Text dat
if __name__ is not '__main__':
    devices = None
    parameter_update_required = False
    last_params = dict()

# Executes in python console outside of TouchDesigner (for testing)
if __name__ is '__main__':
    openni2.initialize(dll_directories='../Redist')
    devs = Devices()

    parameter_update_required = False
