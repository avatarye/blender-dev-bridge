from pathlib import Path
import subprocess
import sys

import bpy

if bpy.app.version[0] < 4 or bpy.app.version[1] < 2:
    bl_info = {
        'name': 'Blender Dev Bridge',
        'author': 'Yongqing Ye, avatar.ye@gmail.com',
        'version': (1, 0, 0),
        'blender': (4, 0, 0),
        'category': 'Development',
    }

    __title__ = bl_info['name']
    __author__ = bl_info['author']
    __version__ = bl_info['version']


class BlenderDevBridgeAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    pydev_pycharm_version: bpy.props.StringProperty(
        name='Version of pydevd_pycharm',
        description='The version of pydevd-pycharm library, such as "241.18034.82"',
    )
    server_name: bpy.props.StringProperty(
        name='Server name',
        description='The name of the server to connect to, such as "localhost"',
    )
    port: bpy.props.IntProperty(
        name='Port',
        min=1000,
        description='The port number to connect to, such as 20240',
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'pydev_pycharm_version')
        row = layout.row()
        row.operator('wm.blender_dev_bridge', text='Install pydevd_pycharm', icon='ADD').action = 'install'
        row.operator('wm.blender_dev_bridge', text='Uninstall pydevd_pycharm',
                        icon='REMOVE').action = 'uninstall'
        row = layout.row()
        row.prop(self, 'server_name')
        row.prop(self, 'port')
        layout.label(text='Please ensure the following:')
        layout.label(text='1. The server name and port match the settings of the Python Debug Server in PyCharm.')
        layout.label(text='2. Install the correct version of pydevd_pycharm required by PyCharm.')
        layout.label(text='3. Set up the correct path mapping in the Python Debug Server.')


class WM_OT_blender_dev_bridge(bpy.types.Operator):
    bl_idname = 'wm.blender_dev_bridge'
    bl_label = 'Connect to PyCharm Debugger'
    bl_description = 'Connects to a PyCharm debugger for remote debugging'

    action: bpy.props.StringProperty()

    def import_pydevd_pycharm(self) -> bool:
        try:
            import pydevd_pycharm
            return True
        except ImportError:
            return False

    def execute(self, context):
        addon_prefs = context.preferences.addons[__name__].preferences
        if self.action == 'install':
            self.action = ''  # Clear the action after installation, so the default action is connect
            if not addon_prefs.pydev_pycharm_version:
                self.report({'ERROR'}, 'Please set the PyCharm version in the addon preferences.')
                return {'CANCELLED'}
            local_site_packages_path = Path(sys.executable).parent.parent / 'lib' / 'site-packages'
            if not local_site_packages_path.exists():
                self.report({'ERROR'}, 'Failed to find the site-packages directory. Please check the console for more '
                                       'information.')
                return {'CANCELLED'}
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', '--force-reinstall',
                                     f'--target={str(local_site_packages_path)}',
                                     f'pydevd-pycharm~={addon_prefs.pydev_pycharm_version}'], check=True)
            if result.returncode != 0:
                self.report({'ERROR'}, 'Failed to install pydevd-pycharm. Please check the console for more '
                                       'information.')
                return {'CANCELLED'}
            else:
                self.report({'INFO'}, 'Successfully installed pydevd-pycharm.')
                return {'FINISHED'}
        elif self.action == 'uninstall':
            self.action = ''  # Clear the action after installation, so the default action is connect
            result = subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'pydevd-pycharm'], check=True)
            if result.returncode != 0:
                self.report({'ERROR'}, 'Failed to uninstall pydevd-pycharm. Please check the console for more '
                                       'information.')
                return {'CANCELLED'}
            else:
                self.report({'INFO'}, 'Successfully uninstalled pydevd-pycharm.')
                return {'FINISHED'}
        else:  # This is the default action which is called by user through the UI to connect to PyCharm debugger
            if self.import_pydevd_pycharm():
                import pydevd_pycharm
                if not addon_prefs.server_name:
                    self.report({'ERROR'}, 'Please set the server name in the addon preferences.')
                    return {'CANCELLED'}
                if not addon_prefs.port:
                    self.report({'ERROR'}, 'Please set the port in the addon preferences.')
                    return {'CANCELLED'}
                try:
                    pydevd_pycharm.settrace(addon_prefs.server_name, port=addon_prefs.port, stdoutToServer=True,
                                            stderrToServer=True, suspend=False)
                    self.report({'INFO'}, 'Connected to PyCharm debugger at '
                                          f'{addon_prefs.server_name}:{addon_prefs.port}.')
                    return {'FINISHED'}
                except Exception as e:
                    self.report({'ERROR'}, f'Failed to connect to PyCharm debugger: {e}')
                    return {'CANCELLED'}
            else:
                self.report({'ERROR'}, 'Unable to import pydevd_pycharm. Please make sure pydevd_pycharm is installed.')
                return {'CANCELLED'}


classes = (BlenderDevBridgeAddonPreferences, WM_OT_blender_dev_bridge)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
