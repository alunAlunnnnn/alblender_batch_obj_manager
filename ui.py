import bpy


class AL_PT_batch_obj_panel(bpy.types.Panel):
    """3D 视图侧边栏面板"""
    bl_label = "Batch OBJ Manager"
    bl_idname = "AL_PT_batch_obj_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AL Tools"

    def draw(self, context):
        layout = self.layout

        layout.label(text="High-Performance IO", icon='MESH_DATA')

        col = layout.column(align=True)
        col.scale_y = 1.2

        col.operator("import_scene.batch_obj", text="Batch Import OBJ", icon='IMPORT')
        col.operator("export_scene.batch_obj", text="Batch Export OBJ", icon='EXPORT')

        layout.separator()

        box = layout.box()
        selected_meshes = len([o for o in context.selected_objects if o.type == 'MESH'])
        box.label(text=f"Selected Meshes: {selected_meshes}", icon='RESTRICT_SELECT_OFF')