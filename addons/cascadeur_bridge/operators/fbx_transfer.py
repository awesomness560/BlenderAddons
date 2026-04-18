import bpy

from .addon_properties import get_csc_export_settings
from ..utils import file_handling
from ..utils.server_socket import ServerSocket
from ..utils.csc_handling import CascadeurHandler
from .. import addon_info

from typing import Optional, Iterable


def import_fbx(file_path: str) -> list:
    """
    Importing the provided file with the fbx import settings set on the N panel.

    :param str file_path: FBX file path to be imported
    :return list: List of selected objects in the scene
    """
    addon_props = bpy.context.scene.cbb_fbx_settings
    bpy.ops.import_scene.fbx(
        filepath=file_path,
        # Transform
        global_scale=addon_props.cbb_import_global_scale,
        bake_space_transform=addon_props.cbb_import_apply_transform,
        use_manual_orientation=addon_props.cbb_import_manual_orientation,
        axis_forward=addon_props.cbb_import_axis_forward,
        axis_up=addon_props.cbb_import_axis_up,
        # Animation
        use_anim=addon_props.cbb_import_use_anim,
        anim_offset=addon_props.cbb_import_anim_offset,
        # Armature
        ignore_leaf_bones=addon_props.cbb_import_ignore_leaf_bones,
        force_connect_children=addon_props.cbb_import_force_connect_children,
        automatic_bone_orientation=addon_props.cbb_import_automatic_bone_orientation,
        primary_bone_axis=addon_props.cbb_import_primary_bone_axis,
        secondary_bone_axis=addon_props.cbb_import_secondary_bone_axis,
        use_prepost_rot=addon_props.cbb_import_use_prepost_rot,
    )
    # Return the list of imported objects
    return bpy.context.selected_objects


def _find_first_armature(objects: Iterable[bpy.types.Object]) -> Optional[bpy.types.Object]:
    for obj in objects:
        if obj and obj.type == "ARMATURE":
            return obj
    return None


def _ensure_current_action(armature_obj: bpy.types.Object) -> bpy.types.Action:
    if not armature_obj.animation_data:
        armature_obj.animation_data_create()
    if not armature_obj.animation_data.action:
        armature_obj.animation_data.action = bpy.data.actions.new(
            name=f"{armature_obj.name}_Action"
        )
    return armature_obj.animation_data.action


def _clear_action(action: bpy.types.Action) -> None:
    for fc in list(action.fcurves):
        action.fcurves.remove(fc)


def _shift_action_frames(action: bpy.types.Action, delta: float) -> None:
    if not action or not delta:
        return
    for fc in action.fcurves:
        for kp in fc.keyframe_points:
            kp.co.x += delta
            kp.handle_left.x += delta
            kp.handle_right.x += delta
        fc.update()


def _select_only(obj: bpy.types.Object) -> None:
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _retarget_and_bake_pose(
    *,
    source_armature_obj: bpy.types.Object,
    target_armature_obj: bpy.types.Object,
    frame_start: int,
    frame_end: int,
) -> None:
    # Add constraints to target bones that exist on source.
    _select_only(target_armature_obj)
    bpy.ops.object.mode_set(mode="POSE")

    source_pose_bones = source_armature_obj.pose.bones
    target_pose_bones = target_armature_obj.pose.bones

    for pb in target_pose_bones:
        if pb.name not in source_pose_bones:
            continue
        c = pb.constraints.new(type="COPY_TRANSFORMS")
        c.target = source_armature_obj
        c.subtarget = pb.name

    # Ensure all bones are selected for baking with only_selected=True.
    for pb in target_pose_bones:
        pb.bone.select = True

    bpy.ops.nla.bake(
        frame_start=frame_start,
        frame_end=frame_end,
        only_selected=True,
        visual_keying=True,
        clear_constraints=True,
        use_current_action=True,
        bake_types={"POSE"},
    )

    bpy.ops.object.mode_set(mode="OBJECT")


def delete_objects(objects: list) -> None:
    """
    Delete the provided list of objects.

    :param list objects: List of objects
    """
    # Create a copy of the objects list
    objects_copy = objects.copy()

    for obj in objects_copy:
        # Check if the object exists in Blender's data before attempting to remove it
        obj_in_data = bpy.data.objects.get(obj.name)
        if obj_in_data:
            bpy.data.objects.remove(obj, do_unlink=True)
            # Remove the object from the original list to avoid reprocessing
            objects.remove(obj)

    # Update the scene to reflect the changes
    bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)


class OperatorBaseClass(bpy.types.Operator):
    server_socket = None
    file_path = None

    def __del__(self):
        try:
            if self.server_socket:
                self.server_socket.close()
        except Exception:
            pass
        addon_info.operation_completed = True

    def _cleanup(self) -> None:
        try:
            if self.server_socket:
                self.server_socket.close()
        finally:
            self.server_socket = None
            addon_info.operation_completed = True

    def start_operator(self):
        addon_info.operation_completed = False

        # Fail early with a readable error if Cascadeur isn't configured.
        try:
            CascadeurHandler()._require_valid_cascadeur_path()
        except Exception as e:
            self.report({"ERROR"}, str(e))
            addon_info.operation_completed = True
            return {"CANCELLED"}

        try:
            # If Blender kept an old operator instance around, make sure the port is free.
            if self.server_socket:
                self.server_socket.close()
            self.server_socket = ServerSocket()
        except Exception as e:
            self.report({"ERROR"}, str(e))
            addon_info.operation_completed = True
            return {"CANCELLED"}


class CBB_OT_retarget_config_add(bpy.types.Operator):
    bl_idname = "cbb.retarget_config_add"
    bl_label = "Add Retarget Config"

    def execute(self, context):
        cfg = context.scene.cbb_retarget_configs.add()
        context.scene.cbb_retarget_configs_index = len(context.scene.cbb_retarget_configs) - 1
        if context.active_object and context.active_object.type == "ARMATURE":
            cfg.target_armature = context.active_object
        return {"FINISHED"}


class CBB_OT_retarget_config_remove(bpy.types.Operator):
    bl_idname = "cbb.retarget_config_remove"
    bl_label = "Remove Retarget Config"

    def execute(self, context):
        items = context.scene.cbb_retarget_configs
        if not items:
            return {"CANCELLED"}
        items.remove(len(items) - 1)
        context.scene.cbb_retarget_configs_index = max(0, len(items) - 1)
        return {"FINISHED"}


class CBB_OT_import_retarget_bake_config(OperatorBaseClass):
    """Import animation from Cascadeur and retarget/bake to a configured armature."""

    bl_idname = "cbb.import_cascadeur_retarget_bake_config"
    bl_label = "Import (Config)"

    config_index: bpy.props.IntProperty(default=0)
    force_selected_interval: bpy.props.BoolProperty(
        name="Selected interval export",
        description=(
            "If enabled, export from Cascadeur using only the timeline's selected frame range "
            "(same as enabling Export selected intervals for this run only)"
        ),
        default=False,
    )

    target_armature_obj: Optional[bpy.types.Object] = None
    imported_objects: list[bpy.types.Object] = []
    _actions_before: set[bpy.types.Action] = set()
    _preserve_existing_keys: bool = False
    _start_frame: int = 0

    @classmethod
    def poll(cls, context):
        return hasattr(context.scene, "cbb_retarget_configs")

    def modal(self, context, event):
        if event.type == "ESC":
            self._cleanup()
            return {"CANCELLED"}

        self.server_socket.run()

        if self.server_socket.client_socket:
            export_settings = (
                get_csc_export_settings(force_selected_interval=True)
                if self.force_selected_interval
                else get_csc_export_settings()
            )
            self.server_socket.send_message(export_settings)
            data = self.server_socket.receive_message()
            if data:
                if not isinstance(data, list):
                    self.report({"ERROR"}, f"Unexpected response: {str(data)}")
                    addon_info.operation_completed = True
                    return {"CANCELLED"}

                fbx_path = data[0]
                imported = import_fbx(fbx_path)
                self.imported_objects.extend(imported)
                file_handling.delete_file(fbx_path)

                source_armature_obj = _find_first_armature(imported)
                if not source_armature_obj:
                    self.report({"ERROR"}, "No armature found in imported FBX.")
                    delete_objects(self.imported_objects)
                    self._cleanup()
                    return {"CANCELLED"}

                if not self.target_armature_obj or self.target_armature_obj.type != "ARMATURE":
                    self.report({"ERROR"}, "Invalid target armature in config.")
                    delete_objects(self.imported_objects)
                    self._cleanup()
                    return {"CANCELLED"}

                target_action = _ensure_current_action(self.target_armature_obj)
                if not self._preserve_existing_keys:
                    _clear_action(target_action)

                src_action = None
                if source_armature_obj.animation_data:
                    src_action = source_armature_obj.animation_data.action

                if src_action:
                    src_start = int(src_action.frame_range[0])
                    src_end = int(src_action.frame_range[1])
                else:
                    src_start = int(context.scene.frame_start)
                    src_end = int(context.scene.frame_end)

                if self._start_frame > 0:
                    desired_start = int(self._start_frame)
                elif self._preserve_existing_keys:
                    desired_start = int(context.scene.frame_current)
                else:
                    desired_start = int(src_start)

                delta = float(desired_start - src_start)
                if src_action and delta:
                    _shift_action_frames(src_action, delta)
                    src_start = desired_start
                    src_end = int(src_end + delta)

                try:
                    _retarget_and_bake_pose(
                        source_armature_obj=source_armature_obj,
                        target_armature_obj=self.target_armature_obj,
                        frame_start=int(src_start),
                        frame_end=int(src_end),
                    )
                except Exception as e:
                    self.report({"ERROR"}, f"Retarget/bake failed: {e}")
                    delete_objects(self.imported_objects)
                    self._cleanup()
                    return {"CANCELLED"}

                delete_objects(self.imported_objects)
                for act in list(bpy.data.actions):
                    if act not in self._actions_before and act != target_action:
                        try:
                            bpy.data.actions.remove(act)
                        except Exception:
                            pass

                self.target_armature_obj.select_set(True)
                bpy.context.view_layer.objects.active = self.target_armature_obj
                self.report({"INFO"}, "Finished")
                self._cleanup()
                return {"FINISHED"}

        return {"PASS_THROUGH"}

    def execute(self, context):
        self.start_operator()
        items = context.scene.cbb_retarget_configs
        idx = int(self.config_index)
        if idx < 0 or idx >= len(items):
            self.report({"ERROR"}, "Invalid config index.")
            addon_info.operation_completed = True
            return {"CANCELLED"}

        cfg = items[idx]
        if not cfg.target_armature or cfg.target_armature.type != "ARMATURE":
            self.report({"ERROR"}, "Pick a target armature in this config.")
            addon_info.operation_completed = True
            return {"CANCELLED"}

        self.target_armature_obj = cfg.target_armature
        self._preserve_existing_keys = bool(cfg.preserve_existing_keys)
        self._start_frame = int(cfg.start_frame)
        self._actions_before = set(bpy.data.actions)

        CascadeurHandler().execute_csc_command("commands.externals.temp_exporter")
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}
