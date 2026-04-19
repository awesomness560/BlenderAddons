import bpy
from ..utils.csc_handling import CascadeurHandler
from ..utils.config_handling import get_panel_name
from .. import addon_info


class PanelBasics:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = get_panel_name()


class CBB_PT_parent_panel(PanelBasics, bpy.types.Panel):
    bl_idname = "CBB_PT_parent"
    bl_label = "Cascadeur Bridge"

    def draw_header(self, context):
        self.layout.label(text="", icon="MODIFIER_DATA")

    def draw(self, context):
        _ch = CascadeurHandler()
        layout = self.layout
        col = layout.column(align=False)
        if not _ch.is_csc_exe_path_valid:
            col.label(
                icon="ERROR", text="Set a valid Cascadeur exe path in preferences!"
            )
            col.separator()

        row = col.row()
        row.operator(
            "cbb.start_cascadeur",
            text="Start Cascadeur",
            icon="MESH_UVSPHERE",
        )
        row.scale_y = 1.5
        col.separator()

        if not addon_info.operation_completed:
            col.label(icon="LOCKED", text="Operation in progress!")
            col.separator()

        addon_props = context.scene.cbb_fbx_settings
        skip_box = layout.box()
        skip_box.label(text="Skip retargets")
        row = skip_box.row(align=True)
        row.prop(
            addon_props,
            "cbb_retarget_exclude_substrings",
            text="Keywords",
        )
        row.operator(
            "cbb.save_retarget_skip_keywords",
            text="Save",
            icon="FILE_TICK",
        )
        skip_box.label(
            text="If a linked rig collapses, try Append (even with Library Override some assets need it).",
            icon="INFO",
        )

        box = layout.box()
        header = box.row(align=True)
        header.label(text="Retarget Configs")
        header.operator("cbb.retarget_config_add", text="", icon="ADD")
        header.operator("cbb.retarget_config_remove", text="", icon="REMOVE")

        configs = context.scene.cbb_retarget_configs
        for idx, cfg in enumerate(configs):
            row_box = box.box()
            row = row_box.row(align=True)
            row.prop(cfg, "target_armature", text="")
            btns = row.row(align=True)
            op = btns.operator(
                "cbb.import_cascadeur_retarget_bake_config",
                text="Import",
                icon="IMPORT",
            )
            op.config_index = idx
            op.force_selected_interval = False
            op = btns.operator(
                "cbb.import_cascadeur_retarget_bake_config",
                text="Interval",
                icon="PREVIEW_RANGE",
            )
            op.config_index = idx
            op.force_selected_interval = True

            row = row_box.row(align=True)
            row.prop(cfg, "preserve_existing_keys", text="Preserve keys (insert)")
            row.prop(cfg, "start_frame", text="Start")


class CBB_PT_workflow_settings(PanelBasics, bpy.types.Panel):
    """FBX and socket settings used by Retarget Config imports."""

    bl_idname = "CBB_PT_workflow_settings"
    bl_label = "Export / Import / Connection"
    bl_parent_id = "CBB_PT_parent"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.label(text="", icon="SETTINGS")

    def draw(self, context):
        addon_props = context.scene.cbb_fbx_settings
        layout = self.layout

        box = layout.box()
        box.label(text="Cascadeur → Blender (export from Cascadeur)")
        col = box.column(align=True)
        col.prop(addon_props, "cbb_export_methods")
        col.prop(addon_props, "cbb_csc_apply_euler_filter")
        col.prop(addon_props, "cbb_csc_up_axis")
        col.prop(addon_props, "cbb_csc_bake_animation")
        col.prop(addon_props, "cbb_csc_import_selected")

        box = layout.box()
        box.label(text="Blender FBX import (temporary rig from Cascadeur)")
        col = box.column(align=True)
        col.prop(addon_props, "cbb_import_global_scale")
        col.prop(addon_props, "cbb_import_apply_transform")
        col.prop(addon_props, "cbb_import_manual_orientation")
        col.prop(addon_props, "cbb_import_axis_forward")
        col.prop(addon_props, "cbb_import_axis_up")
        col.prop(addon_props, "cbb_import_use_anim")
        col.prop(addon_props, "cbb_import_anim_offset")
        col.prop(addon_props, "cbb_import_ignore_leaf_bones")
        col.prop(addon_props, "cbb_import_force_connect_children")
        col.prop(addon_props, "cbb_import_automatic_bone_orientation")
        col.prop(addon_props, "cbb_import_primary_bone_axis")
        col.prop(addon_props, "cbb_import_secondary_bone_axis")
        col.prop(addon_props, "cbb_import_use_prepost_rot")

        box = layout.box()
        box.label(text="Connection & presets")
        row = box.row(align=True)
        row.prop(addon_props, "cbb_port")
        row.operator("cbb.save_port_settings", text="", icon="FILE_TICK")
        row = box.row(align=True)
        row.operator("cbb.save_fbx_settings", text="Save settings", icon="FAKE_USER_ON")
        row.operator("cbb.reset_fbx_settings", text="Reset", icon="FILE_REFRESH")
