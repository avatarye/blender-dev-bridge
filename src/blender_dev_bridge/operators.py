# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.


import bpy

from .app_window import AppWindow
from .common import *


@bpy.app.handlers.persistent
def check_current_blender_dir(args):
    """
    The handler function that is registered to the load_post and save_post events to refresh the file browser in the
    ASIN Downloader app window.
    """
    if APP_WINDOW:
        APP_WINDOW.check_current_blender_dir()


class WM_OT_Aseet_Downlader(bpy.types.Operator):
    """Click to open ASIN Downloader window"""

    bl_label = 'ASIN Downloader'
    bl_idname = 'wm.asin_downloader'

    def _open_app_window(self):
        global QT_APP, APP_WINDOW
        QT_APP = start_qt_app()
        APP_WINDOW = AppWindow()
        APP_WINDOW.show()
        APP_WINDOW.raise_()
        APP_WINDOW.activateWindow()

    def execute(self, context):
        # Open the ASIN Downloader Qt window
        self._open_app_window()
        # Register the handler function to refresh the file browser in the ASIN Downloader app window
        bpy.app.handlers.load_post.append(check_current_blender_dir)
        bpy.app.handlers.save_post.append(check_current_blender_dir)
        return {'FINISHED'}
