import bpy
import os
from bpy.props import StringProperty, BoolProperty, IntProperty, FloatProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper
from .utils import find_obj_files, get_logger

logger = get_logger()


class IMPORT_SCENE_OT_batch_obj(bpy.types.Operator, ImportHelper):
    """批量高效导入 OBJ 文件"""
    bl_idname = "import_scene.batch_obj"
    bl_label = "Batch Import OBJ"
    bl_options = {'REGISTER'}

    filter_glob: StringProperty(default="*.obj", options={'HIDDEN'})
    directory: StringProperty(subtype='DIR_PATH')

    use_recursive: BoolProperty(name="Recursive", description="搜索子文件夹", default=True)
    max_depth: IntProperty(name="Max Depth", description="-1: 无限制", default=-1, min=-1)

    global_scale: FloatProperty(name="Scale", default=1.000, min=0.0001)
    clamp_size: FloatProperty(name="Clamp Bounding Box", default=0.000, min=0.0)

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

    use_split_objects: BoolProperty(name="Split By Object", default=True)
    use_split_groups: BoolProperty(name="Split By Group", default=False)
    import_vertex_groups: BoolProperty(name="Vertex Groups", default=False)
    validate_meshes: BoolProperty(name="Validate Meshes", default=True)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Batch Search Settings", icon='VIEWZOOM')
        box.prop(self, "use_recursive")
        row = box.row()
        row.enabled = self.use_recursive
        row.prop(self, "max_depth")

        layout.separator()
        box = layout.box()
        box.label(text="Transform", icon='OBJECT_ORIGIN')
        box.prop(self, "global_scale")
        box.prop(self, "clamp_size")
        box.prop(self, "axis_forward")
        box.prop(self, "axis_up")

        box = layout.box()
        box.label(text="Options", icon='MODIFIER')
        box.prop(self, "use_split_objects")
        box.prop(self, "use_split_groups")
        box.prop(self, "import_vertex_groups")
        box.prop(self, "validate_meshes")

    def execute(self, context):
        if not self.directory or not os.path.isdir(self.directory):
            self.report({'ERROR'}, "Invalid Directory!")
            return {'CANCELLED'}

        obj_files = find_obj_files(self.directory, self.use_recursive, self.max_depth)
        total_files = len(obj_files)

        if total_files == 0:
            self.report({'WARNING'}, "No OBJ files found.")
            return {'CANCELLED'}

        logger.info(f"Starting batch import of {total_files} files...")
        wm = context.window_manager
        wm.progress_begin(0, total_files)

        success_count = 0
        error_streak = 0
        MAX_ERROR_STREAK = 5  # 熔断阈值

        for i, filepath in enumerate(obj_files):
            if error_streak >= MAX_ERROR_STREAK:
                self.report({'ERROR'}, f"Aborted: {MAX_ERROR_STREAK} consecutive errors hit.")
                logger.error("Circuit breaker triggered. Aborting batch import.")
                break

            try:
                if hasattr(bpy.ops.wm, "obj_import"):
                    bpy.ops.wm.obj_import(
                        filepath=filepath,
                        global_scale=self.global_scale,
                        clamp_size=self.clamp_size,
                        forward_axis=self.axis_forward,
                        up_axis=self.axis_up,
                        use_split_objects=self.use_split_objects,
                        use_split_groups=self.use_split_groups,
                        import_vertex_groups=self.import_vertex_groups,
                        validate_meshes=self.validate_meshes
                    )
                else:
                    bpy.ops.import_scene.obj(
                        filepath=filepath, global_scale=self.global_scale, clamp_size=self.clamp_size,
                        axis_forward=self.axis_forward, axis_up=self.axis_up,
                        use_split_objects=self.use_split_objects, use_split_groups=self.use_split_groups
                    )
                success_count += 1
                error_streak = 0  # 成功则重置错误计数
            except Exception as e:
                error_streak += 1
                logger.error(f"Failed to import {filepath}: {e}")

            wm.progress_update(i + 1)

        wm.progress_end()
        self.report({'INFO'}, f"Imported {success_count}/{total_files} files.")
        return {'FINISHED'}