import bpy
from typing import Optional

from ..utils import config_handling


def generate_items(options: list) -> list:
    return [(option, option, "") for option in options]


class CBB_PG_fbx_settings(bpy.types.PropertyGroup):
    # Cascadeur Export settings
    cbb_csc_import_selected: bpy.props.BoolProperty(
        name="Export Selected Interval",
        description=(
            "When enabled, Cascadeur exports only the frames selected on its timeline "
            "(used by Retarget Config 'Import' and other bridge imports unless you use the Interval button)"
        ),
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_csc_import_selected",
            bool,
            fallback=False,
        ),
    )

    cbb_csc_apply_euler_filter: bpy.props.BoolProperty(
        name="Apply Euler Filter",
        description="Automatically set objects' rotations to lowes possible values",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_csc_apply_euler_filter",
            bool,
            fallback=False,
        ),
    )

    cbb_csc_up_axis: bpy.props.EnumProperty(
        items=generate_items(["Y", "Z"]),
        name="Up Axis",
        description="Up Axis when exporting from Cascadeur",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_csc_up_axis",
            str,
            fallback="Y",
        ),
    )

    cbb_csc_bake_animation: bpy.props.BoolProperty(
        name="Bake animation",
        description="Key all frames when exporting from Cascadeur",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_csc_bake_animation",
            bool,
            fallback=True,
        ),
    )

    # Blender Import settings
    cbb_import_global_scale: bpy.props.FloatProperty(
        name="Global Scale",
        description="Scale",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_global_scale",
            float,
            fallback=1.0,
        ),
        min=0.001,
        max=1000,
    )

    cbb_import_apply_transform: bpy.props.BoolProperty(
        name="Apply Transform",
        description="Bake space transform into object data. EXPERIMENTAL!",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_apply_transform",
            bool,
            fallback=False,
        ),
    )

    cbb_import_manual_orientation: bpy.props.BoolProperty(
        name="Use Manual Orientation",
        description="Specify orientation and scale, instead of using embedded data in FBX file",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_manual_orientation",
            bool,
            fallback=False,
        ),
    )

    cbb_import_axis_forward: bpy.props.EnumProperty(
        items=generate_items(["X", "Y", "Z", "-X", "-Y", "-Z"]),
        name="Forward",
        description="Forward Axis",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_axis_forward",
            str,
            fallback="-Z",
        ),
    )

    cbb_import_axis_up: bpy.props.EnumProperty(
        items=generate_items(["X", "Y", "Z", "-X", "-Y", "-Z"]),
        name="Up",
        description="Forward Up",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_axis_up",
            str,
            fallback="Y",
        ),
    )

    cbb_import_use_anim: bpy.props.BoolProperty(
        name="Import Animation",
        description="Import FBX animation",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_use_anim",
            bool,
            fallback=True,
        ),
    )

    cbb_import_anim_offset: bpy.props.FloatProperty(
        name="Animation Offset",
        description=" Offset to apply to animation during import, in frames",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_anim_offset",
            float,
            fallback=1.0,
        ),
    )

    cbb_import_ignore_leaf_bones: bpy.props.BoolProperty(
        name="Ignore Leaf Bones",
        description="Ignore the last bone at the end of each chain",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_ignore_leaf_bones",
            bool,
            fallback=True,
        ),
    )

    cbb_import_force_connect_children: bpy.props.BoolProperty(
        name="Force Connect Children",
        description="Force connection of children bones to their parent",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_force_connect_children",
            bool,
            fallback=False,
        ),
    )

    cbb_import_automatic_bone_orientation: bpy.props.BoolProperty(
        name="Automatic Bone Orientation",
        description="Try to align the major bone axis with the bone children",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_automatic_bone_orientation",
            bool,
            fallback=False,
        ),
    )

    cbb_import_primary_bone_axis: bpy.props.EnumProperty(
        items=generate_items(["X", "Y", "Z", "-X", "-Y", "-Z"]),
        name="Primary Bone Axis",
        description="",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_primary_bone_axis",
            str,
            fallback="Y",
        ),
    )

    cbb_import_secondary_bone_axis: bpy.props.EnumProperty(
        items=generate_items(["X", "Y", "Z", "-X", "-Y", "-Z"]),
        name="Secondary Bone Axis",
        description="",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_secondary_bone_axis",
            str,
            fallback="X",
        ),
    )

    cbb_import_use_prepost_rot: bpy.props.BoolProperty(
        name="Use Pre/Post Rotation",
        description="Use pre/post rotation from FBX transform",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_import_use_prepost_rot",
            bool,
            fallback=True,
        ),
    )

    cbb_export_methods: bpy.props.EnumProperty(
        name="Cascadeur Export Method",
        items=(
            ("export_all_objects", "Export All Objects", ""),
            ("export_joints", "Animation", ""),
            ("export_joints_selected", "Animation - selected joints and frames", ""),
            ("export_joints_selected_frames", "Animation - selected frames", ""),
            ("export_joints_selected_objects", "Animation - selected joints", ""),
            ("export_model", "Model", ""),
            ("export_scene_selected", "Scene - selected objects and frames", ""),
            ("export_scene_selected_frames", "Scene - selected frames", ""),
            ("export_scene_selected_objects", "Scene - selected objects", ""),
        ),
        description="Method to use when exporting from Cascadeur",
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_export_methods",
            str,
            fallback="export_all_objects",
        ),
    )  # type: ignore

    cbb_retarget_exclude_substrings: bpy.props.StringProperty(
        name="Skip retargets",
        description=(
            "Comma-separated substrings. Target bones whose names contain any keyword "
            "(case-insensitive) are not retargeted or keyed. Example: hair, skirt, cloth. "
            "Use Save Skip Retargets to store in settings.cfg."
        ),
        default=config_handling.get_config_parameter(
            "FBX Settings",
            "cbb_retarget_exclude_substrings",
            str,
            fallback="",
        ),
    )

    cbb_port: bpy.props.IntProperty(
        name="Port",
        description="Port number used for communicating with Cascadeur",
        default=config_handling.get_config_parameter(
            "Addon Settings",
            "port",
            int,
            fallback=53145,
        ),
        min=0,
        max=65535,
    )


class CBB_PG_retarget_config(bpy.types.PropertyGroup):
    target_armature: bpy.props.PointerProperty(
        name="Armature",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == "ARMATURE",
    )

    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        description="If > 0, inserts animation starting at this frame. If 0, uses the timeline cursor when Preserve Keys is enabled; otherwise uses the source frame range.",
        default=0,
        min=0,
    )

    preserve_existing_keys: bpy.props.BoolProperty(
        name="Preserve Keys",
        description="Don't erase existing keyframes; insert the imported animation starting at Start Frame (if set) or the timeline cursor.",
        default=False,
    )


def register_props():
    bpy.utils.register_class(CBB_PG_fbx_settings)
    bpy.types.Scene.cbb_fbx_settings = bpy.props.PointerProperty(
        type=CBB_PG_fbx_settings
    )
    bpy.utils.register_class(CBB_PG_retarget_config)
    bpy.types.Scene.cbb_retarget_configs = bpy.props.CollectionProperty(
        type=CBB_PG_retarget_config
    )
    bpy.types.Scene.cbb_retarget_configs_index = bpy.props.IntProperty(default=0)


def unregister_props():
    try:
        del bpy.types.Scene.cbb_retarget_configs
        del bpy.types.Scene.cbb_retarget_configs_index
    except Exception:
        pass
    bpy.utils.unregister_class(CBB_PG_retarget_config)
    bpy.utils.unregister_class(CBB_PG_fbx_settings)


def get_csc_export_settings(force_selected_interval: Optional[bool] = None) -> dict:
    settings = {}
    addon_props = bpy.context.scene.cbb_fbx_settings
    if force_selected_interval is None:
        settings["selected_interval"] = addon_props.cbb_csc_import_selected
    else:
        settings["selected_interval"] = bool(force_selected_interval)
    settings["euler_filter"] = addon_props.cbb_csc_apply_euler_filter
    settings["up_axis"] = addon_props.cbb_csc_up_axis
    settings["bake_animation"] = addon_props.cbb_csc_bake_animation
    settings["export_method"] = addon_props.cbb_export_methods
    return settings


class CBB_OT_save_fbx_settings(bpy.types.Operator):
    """Save fbx import and export settings for Cascadeur and Blender"""

    bl_idname = "cbb.save_fbx_settings"
    bl_label = "Save Settings for CSC Bridge"

    def execute(self, context):
        try:
            config_handling.save_fbx_settings()
        except Exception as e:
            self.report({"ERROR"}, f"Couldn't save settings: {e}")
            return {"CANCELLED"}
        self.report({"INFO"}, "Settings saved")
        return {"FINISHED"}


class CBB_OT_reset_fbx_settings(bpy.types.Operator):
    """Reset fbx import and export settings for Cascadeur and Blender"""

    bl_idname = "cbb.reset_fbx_settings"
    bl_label = "Reset FBX Settings of CSC Bridge"

    def execute(self, context):
        try:
            config_handling.reset_fbx_settings()
            # Update UI panel
            bpy.context.area.tag_redraw()
        except Exception as e:
            self.report({"ERROR"}, f"Couldn't save settings: {e}")
            return {"CANCELLED"}
        self.report({"INFO"}, "Settings reset")
        return {"FINISHED"}


class CBB_OT_save_port_number(bpy.types.Operator):
    """Save port settings for Cascadeur and Blender"""

    bl_idname = "cbb.save_port_settings"
    bl_label = "Save Port"

    def execute(self, context):
        result = config_handling.save_port_number()

        if not result:
            self.report(
                {"ERROR"}, "You don't have permission to write the config file."
            )
            self.report({"INFO"}, "Restart Blender as Admin and try again")
            return {"CANCELLED"}
        self.report({"INFO"}, "Settings saved")
        return {"FINISHED"}


class CBB_OT_save_retarget_skip_keywords(bpy.types.Operator):
    """Write Skip retargets keyword list to settings.cfg (FBX Settings section)."""

    bl_idname = "cbb.save_retarget_skip_keywords"
    bl_label = "Save Skip Retargets"

    def execute(self, context):
        try:
            config_handling.save_retarget_skip_keywords()
        except Exception as e:
            self.report({"ERROR"}, f"Couldn't save skip retargets: {e}")
            return {"CANCELLED"}
        self.report({"INFO"}, "Skip retargets saved")
        return {"FINISHED"}
