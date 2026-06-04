bl_info = {
    "name": "AL Batch OBJ Manager",
    "description": "高效批量导入/导出 OBJ 文件，专为海量数据优化",
    "author": "Lun.A",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Sidebar > AL Tools | File > Import/Export",
    "category": "Import-Export",
}

import bpy
from . import utils
from . import importer
from . import exporter
from . import ui

classes = (
    importer.IMPORT_SCENE_OT_batch_obj,
    exporter.EXPORT_SCENE_OT_batch_obj,
    ui.AL_PT_batch_obj_panel,
)

def menu_func_import(self, context):
    self.layout.operator(importer.IMPORT_SCENE_OT_batch_obj.bl_idname, text="Batch Wavefront OBJ (folder)")

def menu_func_export(self, context):
    self.layout.operator(exporter.EXPORT_SCENE_OT_batch_obj.bl_idname, text="Batch Wavefront OBJ (folder)")

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()