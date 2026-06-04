import bpy
import os
import time
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy_extras.io_utils import ExportHelper
from .utils import get_logger

logger = get_logger()


class EXPORT_SCENE_OT_batch_obj(bpy.types.Operator, ExportHelper):
    """批量单体导出为 OBJ 文件"""
    bl_idname = "export_scene.batch_obj"
    bl_label = "Batch Export OBJ"
    bl_options = {'PRESET', 'REGISTER', 'UNDO'}

    filename_ext = ""
    use_filter_folder = True

    batch_mode: EnumProperty(
        name="Export Range",
        items=(('VISIBLE', "All Visible Meshes", ""), ('SELECTED', "Selected Meshes Only", "")),
        default='VISIBLE',
    )

    global_scale: FloatProperty(name="Scale", default=1.000, min=0.0001)
    axis_forward: EnumProperty(
        name="Forward Axis",
        items=(('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", ""), ('NEGATIVE_X', "-X", ""), ('NEGATIVE_Y', "-Y", ""),
               ('NEGATIVE_Z', "-Z", "")),
        default='Y',
    )
    axis_up: EnumProperty(
        name="Up Axis",
        items=(('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", ""), ('NEGATIVE_X', "-X", ""), ('NEGATIVE_Y', "-Y", ""),
               ('NEGATIVE_Z', "-Z", "")),
        default='Z',
    )

    apply_modifiers: BoolProperty(name="Apply Modifiers", default=True)
    export_uv: BoolProperty(name="Export UVs", default=True)
    export_normals: BoolProperty(name="Export Normals", default=True)
    export_colors: BoolProperty(name="Export Colors", default=False)
    export_triangulated_mesh: BoolProperty(name="Triangulate Faces", default=True)

    export_materials: BoolProperty(name="Export Materials", default=True)
    path_mode: EnumProperty(
        name="Path Mode",
        items=(('AUTO', "Auto", ""), ('ABSOLUTE', "Absolute", ""), ('RELATIVE', "Relative", ""), ('MATCH', "Match", ""),
               ('STRIP', "Strip", ""), ('COPY', "Copy", "")),
        default='COPY',
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Batch Settings", icon='OUTLINER_OB_GROUP_INSTANCE')
        box.prop(self, "batch_mode")

        layout.separator()
        box = layout.box()
        box.label(text="Transform", icon='OBJECT_ORIGIN')
        box.prop(self, "global_scale")
        row = box.row()
        row.prop(self, "axis_forward")
        row.prop(self, "axis_up")

        box = layout.box()
        box.label(text="Geometry", icon='MESH_DATA')
        box.prop(self, "apply_modifiers")
        box.prop(self, "export_uv")
        box.prop(self, "export_normals")
        box.prop(self, "export_colors")
        box.prop(self, "export_triangulated_mesh")

        box = layout.box()
        box.label(text="Materials", icon='MATERIAL')
        box.prop(self, "export_materials")
        row = box.row()
        row.enabled = self.export_materials
        row.prop(self, "path_mode")

    def execute(self, context):
        output_dir = self.filepath if os.path.isdir(self.filepath) else os.path.dirname(self.filepath)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if self.batch_mode == 'SELECTED':
            target_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        else:
            target_objects = [obj for obj in context.scene.objects if obj.type == 'MESH' and not obj.hide_get()]

        total_files = len(target_objects)
        if total_files == 0:
            self.report({'WARNING'}, "No matching Mesh objects found.")
            return {'CANCELLED'}

        original_active = context.view_layer.objects.active
        original_selected = context.selected_objects.copy()
        bpy.ops.object.select_all(action='DESELECT')

        wm = context.window_manager
        wm.progress_begin(0, total_files)
        start_time = time.time()

        success_count = 0
        error_streak = 0
        MAX_ERROR_STREAK = 5

        logger.info(f"Exporting {total_files} objects to: {output_dir}")

        for i, obj in enumerate(target_objects):
            if error_streak >= MAX_ERROR_STREAK:
                logger.error("Circuit breaker triggered. Aborting batch export.")
                self.report({'ERROR'}, "Aborted due to consecutive errors.")
                break

            context.view_layer.objects.active = obj
            obj.select_set(True)

            safe_name = bpy.path.clean_name(obj.name)
            obj_filepath = os.path.join(output_dir, f"{safe_name}.obj")

            try:
                if hasattr(bpy.ops.wm, "obj_export"):
                    bpy.ops.wm.obj_export(
                        filepath=obj_filepath,
                        export_selected_objects=True,
                        global_scale=self.global_scale,
                        forward_axis=self.axis_forward,
                        up_axis=self.axis_up,
                        apply_modifiers=self.apply_modifiers,
                        export_uv=self.export_uv,
                        export_normals=self.export_normals,
                        export_colors=self.export_colors,
                        export_triangulated_mesh=self.export_triangulated_mesh,
                        export_materials=self.export_materials,
                        path_mode=self.path_mode,
                    )
                else:
                    bpy.ops.export_scene.obj(
                        filepath=obj_filepath, use_selection=True, global_scale=self.global_scale,
                        axis_forward=self.axis_forward, axis_up=self.axis_up, use_mesh_modifiers=self.apply_modifiers,
                        use_uvs=self.export_uv, use_normals=self.export_normals,
                        use_triangles=self.export_triangulated_mesh,
                        use_materials=self.export_materials, path_mode=self.path_mode
                    )
                success_count += 1
                error_streak = 0
            except Exception as e:
                error_streak += 1
                logger.error(f"Failed to export {obj.name}: {e}")
            finally:
                obj.select_set(False)

            wm.progress_update(i + 1)

        # 恢复状态
        for obj in original_selected:
            obj.select_set(True)
        if original_active:
            context.view_layer.objects.active = original_active

        wm.progress_end()
        elapsed = time.time() - start_time
        self.report({'INFO'}, f"Exported {success_count}/{total_files} models in {elapsed:.2f}s.")
        return {'FINISHED'}