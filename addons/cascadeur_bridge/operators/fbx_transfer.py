import bpy

from .addon_properties import RETARGET_FLAG_PROP, get_csc_export_settings
from ..utils import file_handling
from ..utils import config_handling
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


def _clear_pose_bone_fcurves(action: bpy.types.Action) -> None:
    """Remove only pose-bone animation from *action*, keep object-level F-curves.

    Full action clears were resetting armatures that had been moved in the scene via
    object transform keys (same action as the rig). Retarget only replaces bone motion.
    """
    for fc in list(action.fcurves):
        if fc.data_path.startswith("pose.bones"):
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


def _retarget_exclude_keywords(exclude_string: str) -> list[str]:
    if not exclude_string or not exclude_string.strip():
        return []
    return [t.strip().lower() for t in exclude_string.split(",") if t.strip()]


def _bone_skipped_by_keywords(bone_name: str, keywords: list[str]) -> bool:
    if not keywords:
        return False
    lower = bone_name.lower()
    return any(k in lower for k in keywords)


def _bone_has_retarget_flag(pose_bone: bpy.types.PoseBone) -> bool:
    bone = pose_bone.bone
    if hasattr(bone, RETARGET_FLAG_PROP):
        return bool(getattr(bone, RETARGET_FLAG_PROP))
    return bool(bone.get(RETARGET_FLAG_PROP, False))


def _set_bone_retarget_flag(bone: bpy.types.Bone, enabled: bool) -> bool:
    if hasattr(bone, RETARGET_FLAG_PROP):
        try:
            setattr(bone, RETARGET_FLAG_PROP, enabled)
            return True
        except (AttributeError, TypeError, RuntimeError):
            return False

    try:
        if enabled:
            bone[RETARGET_FLAG_PROP] = True
        elif RETARGET_FLAG_PROP in bone:
            del bone[RETARGET_FLAG_PROP]
        return True
    except (TypeError, RuntimeError):
        return False


def _should_retarget_bone(
    pose_bone: bpy.types.PoseBone,
    source_pose_bones: bpy.types.bpy_prop_collection,
    skip_keywords: list[str],
    filter_mode: str,
) -> bool:
    if pose_bone.name not in source_pose_bones:
        return False

    passes_keywords = not _bone_skipped_by_keywords(pose_bone.name, skip_keywords)
    has_flag = _bone_has_retarget_flag(pose_bone)

    if filter_mode == "KEYWORDS_ONLY":
        return passes_keywords
    if filter_mode == "FLAGS_ONLY":
        return has_flag
    return passes_keywords and has_flag


def _armature_for_flagging(context) -> Optional[bpy.types.Object]:
    obj = context.active_object
    if obj and obj.type == "ARMATURE":
        return obj
    return None


def _selected_bones_for_flagging(
    context, armature_obj: bpy.types.Object
) -> list[bpy.types.Bone]:
    if context.mode == "POSE" and context.active_object == armature_obj:
        return [pb.bone for pb in (context.selected_pose_bones or [])]

    if context.mode == "EDIT_ARMATURE" and context.active_object == armature_obj:
        edit_bones = context.selected_editable_bones or []
        return [
            armature_obj.data.bones[eb.name]
            for eb in edit_bones
            if eb.name in armature_obj.data.bones
        ]

    if context.mode == "OBJECT":
        return [b for b in armature_obj.data.bones if b.select]

    return []


# Object-level paths on bpy.types.Object (not pose bones). FBX often keys these at origin each frame.
_OBJECT_TRANSFORM_FCURVE_PATHS = frozenset(
    {
        "location",
        "rotation_euler",
        "rotation_quaternion",
        "rotation_axis_angle",
        "scale",
        "delta_location",
        "delta_rotation_euler",
        "delta_rotation_quaternion",
        "delta_scale",
    }
)


def _strip_object_transform_fcurves_from_action(armature_obj: bpy.types.Object) -> None:
    """Remove object transform channels from *armature_obj*'s action.

    Imported FBX animation frequently includes keyframes on the armature *object* that keep it
    at the world origin on every frame. That overrides a one-time ``matrix_world`` alignment, so
    Copy Transforms still sees the source at the origin: target object stays put but baked pose
    matches motion around world zero.
    """
    if armature_obj.type != "ARMATURE":
        return
    ad = armature_obj.animation_data
    if not ad or not ad.action:
        return
    action = ad.action
    for fc in list(action.fcurves):
        if fc.data_path in _OBJECT_TRANSFORM_FCURVE_PATHS:
            action.fcurves.remove(fc)


def _retarget_and_bake_pose(
    *,
    source_armature_obj: bpy.types.Object,
    target_armature_obj: bpy.types.Object,
    frame_start: int,
    frame_end: int,
) -> int:
    keywords_csv, filter_mode = config_handling.get_retarget_filter_settings()
    skip_keywords = _retarget_exclude_keywords(keywords_csv)

    # Copy Transforms matches bones in *world* space. Align the source object to the target,
    # and strip object-level keys on the import so per-frame FBX object animation does not
    # keep the source rig at world origin (which would leave bone motion there while the target
    # object transform stays where the user moved it).
    _strip_object_transform_fcurves_from_action(source_armature_obj)
    source_armature_obj.matrix_world = target_armature_obj.matrix_world.copy()
    bpy.context.view_layer.update()

    _select_only(target_armature_obj)
    bpy.ops.object.mode_set(mode="POSE")

    source_pose_bones = source_armature_obj.pose.bones
    target_pose_bones = target_armature_obj.pose.bones

    if filter_mode == "KEYWORDS_ONLY" and not skip_keywords:
        bpy.ops.object.mode_set(mode="OBJECT")
        raise RuntimeError(
            "Skip Keywords Only is active but no skip keywords are set. "
            "Enter keywords in the panel or click Load to read settings.cfg."
        )

    if filter_mode in {"BOTH", "FLAGS_ONLY"}:
        flagged_count = sum(
            1 for pb in target_pose_bones if _bone_has_retarget_flag(pb)
        )
        if flagged_count == 0:
            bpy.ops.object.mode_set(mode="OBJECT")
            raise RuntimeError(
                f"No bones are flagged on target armature '{target_armature_obj.name}'. "
                "Select bones and use Flag Selected on that armature first."
            )

    constrained: list[bpy.types.PoseBone] = []
    for pb in target_pose_bones:
        if not _should_retarget_bone(pb, source_pose_bones, skip_keywords, filter_mode):
            continue
        c = pb.constraints.new(type="COPY_TRANSFORMS")
        c.target = source_armature_obj
        c.subtarget = pb.name
        constrained.append(pb)

    for pb in target_pose_bones:
        pb.bone.select = False
    for pb in constrained:
        pb.bone.select = True

    if not constrained:
        bpy.ops.object.mode_set(mode="OBJECT")
        raise RuntimeError(
            "No bones left to retarget after applying name matching and the active retarget filters."
        )

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
    return len(constrained)


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


class CBB_OT_flag_selected_retarget_bones(bpy.types.Operator):
    bl_idname = "cbb.flag_selected_retarget_bones"
    bl_label = "Flag Selected Bones"
    bl_description = (
        "Mark selected bones on the active armature for flag-based retarget filtering"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _armature_for_flagging(context) is not None

    def execute(self, context):
        armature_obj = _armature_for_flagging(context)
        if not armature_obj:
            self.report({"WARNING"}, "Select the target armature first.")
            return {"CANCELLED"}

        bones = _selected_bones_for_flagging(context, armature_obj)
        if not bones:
            self.report(
                {"WARNING"},
                "Select bones on the target armature (Pose, Edit, or Object mode).",
            )
            return {"CANCELLED"}

        updated = 0
        failed = 0
        for bone in bones:
            if _set_bone_retarget_flag(bone, True):
                updated += 1
            else:
                failed += 1

        msg = f"Flagged {updated} bone(s) on '{armature_obj.name}'."
        if failed:
            msg += f" {failed} bone(s) could not be edited (linked rig may need a library override)."
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class CBB_OT_unflag_selected_retarget_bones(bpy.types.Operator):
    bl_idname = "cbb.unflag_selected_retarget_bones"
    bl_label = "Unflag Selected Bones"
    bl_description = "Clear the retarget flag from selected bones on the active armature"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _armature_for_flagging(context) is not None

    def execute(self, context):
        armature_obj = _armature_for_flagging(context)
        if not armature_obj:
            self.report({"WARNING"}, "Select the target armature first.")
            return {"CANCELLED"}

        bones = _selected_bones_for_flagging(context, armature_obj)
        if not bones:
            self.report(
                {"WARNING"},
                "Select bones on the target armature (Pose, Edit, or Object mode).",
            )
            return {"CANCELLED"}

        updated = 0
        failed = 0
        for bone in bones:
            if _set_bone_retarget_flag(bone, False):
                updated += 1
            else:
                failed += 1

        msg = f"Cleared retarget flag on {updated} bone(s) on '{armature_obj.name}'."
        if failed:
            msg += f" {failed} bone(s) could not be edited (linked rig may need a library override)."
        self.report({"INFO"}, msg)
        return {"FINISHED"}


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
                    _clear_pose_bone_fcurves(target_action)

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
                    bone_count = _retarget_and_bake_pose(
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
                self.report(
                    {"INFO"},
                    f"Finished ({bone_count} bone(s) retargeted on '{self.target_armature_obj.name}')",
                )
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

    def invoke(self, context, event):
        # Ensures RNA properties set from the panel (e.g. force_selected_interval) are applied
        # before execute runs (needed on some Blender builds).
        return self.execute(context)
