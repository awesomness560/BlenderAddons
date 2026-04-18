import bpy

from .addon_properties import get_csc_export_settings
from ..utils import file_handling
from ..utils.server_socket import ServerSocket
from ..utils.csc_handling import CascadeurHandler
from .. import addon_info

import os
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


def export_fbx(file_path: str) -> None:
    """
    Exporting fbx from Blender to the provided path using the settings
    set on the N panel.

    :param str file_path: Path of the fbx file.
    """
    addon_props = bpy.context.scene.cbb_fbx_settings
    bpy.ops.export_scene.fbx(
        filepath=file_path,
        # Include
        use_selection=addon_props.cbb_export_use_selection,
        object_types=addon_props.cbb_export_object_types,
        # Transform
        global_scale=addon_props.cbb_export_global_scale,
        axis_forward=addon_props.cbb_export_axis_forward,
        axis_up=addon_props.cbb_export_axis_up,
        bake_space_transform=addon_props.cbb_export_apply_transform,
        # Armature
        primary_bone_axis=addon_props.cbb_export_primary_bone_axis,
        secondary_bone_axis=addon_props.cbb_export_secondary_bone_axis,
        use_armature_deform_only=addon_props.cbb_export_deform_only,
        add_leaf_bones=addon_props.cbb_export_leaf_bones,
        # Animation
        bake_anim=addon_props.cbb_export_bake_anim,
        bake_anim_use_nla_strips=addon_props.cbb_export_use_nla_strips,
        bake_anim_use_all_actions=addon_props.cbb_export_use_all_actions,
    )


def get_actions_from_armatures(selected_objects: list) -> list:
    """
    Get the actions from all of the selected objects in Blender.

    :param list selected_objects: List of selected objects
    :return list: List of obj.animation_data.action objects
    """
    actions = []
    for obj in selected_objects:
        if hasattr(obj.animation_data, "action"):
            action = obj.animation_data.action
            if obj.type == "ARMATURE":
                actions.append(action)
            else:
                bpy.data.actions.remove(action)
    return actions


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


def apply_action(
    armature: bpy.types.Armature,
    action: bpy.types.Action,
    action_name: str = "cascadeur_action",
) -> None:
    """
    Apply the provided action to the armature with the given name.

    :param bpy.types.Armature armature: Armature object
    :param bpy.types.Action action: Action object to be set
    :param str action_name: New name of the action, defaults to "cascadeur_action"
    """
    # TODO verify the type of armature and action
    # print(f'Type of armature: {type(armature)}')
    # print(f'Type of action: {type(action)}')
    action.name = action_name
    if not hasattr(armature.animation_data, "action"):
        armature.animation_data_create()
    armature.animation_data.action = action


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


class CBB_OT_export_blender_fbx(OperatorBaseClass):
    """Exports the selected objects and imports them to Cascadeur"""

    bl_idname = "cbb.export_blender_fbx"
    bl_label = "Export to Cascadeur"

    def modal(self, context, event):
        if event.type == "ESC":
            self._cleanup()
            return {"CANCELLED"}

        self.server_socket.run()

        if self.server_socket.client_socket:
            addon_props = bpy.context.scene.cbb_fbx_settings
            import_method_name = addon_props.cbb_import_methods
            message = {
                "file_path": self.file_path,
                "import_method": import_method_name,
            }
            self.server_socket.send_message(message)
            response = self.server_socket.receive_message()
            if response == "SUCCESS":
                print("File successfully imported to Cascadeur.")
                file_handling.delete_file(self.file_path)
                self.report({"INFO"}, "Finished")
                self._cleanup()
                return {"FINISHED"}
            else:
                self._cleanup()
                return {"CANCELLED"}

        return {"PASS_THROUGH"}

    def execute(self, context):
        self.start_operator()

        self.file_path = file_handling.get_export_path()
        try:
            export_fbx(self.file_path)
        except Exception as e:
            self.report({"ERROR"}, "Couldn't export fbx file")
            addon_info.operation_completed = True
            return {"CANCELLED"}
        CascadeurHandler().execute_csc_command("commands.externals.temp_importer")
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}


class CBB_OT_import_cascadeur_fbx(OperatorBaseClass):
    """Imports the currently opened Cascadeur scene"""

    bl_idname = "cbb.import_cascadeur_fbx"
    bl_label = "Import Cascadeur Scene"

    batch_export: bpy.props.BoolProperty(
        name="Import all scene",
        description="",
        default=False,
    )

    def modal(self, context, event):
        if event.type == "ESC":
            self._cleanup()
            return {"CANCELLED"}

        self.server_socket.run()

        if self.server_socket.client_socket:
            self.server_socket.send_message(get_csc_export_settings())
            data = self.server_socket.receive_message()
            if data:
                print(str(data))
                if not isinstance(data, list):
                    self.report({"ERROR"}, f"Unexpected response: {str(data)}")
                    addon_info.operation_completed = True
                    return {"CANCELLED"}

                for file in data:
                    import_fbx(file)
                    file_handling.delete_file(file)
                self.report({"INFO"}, "Finished")
                self._cleanup()
                return {"FINISHED"}

        return {"PASS_THROUGH"}

    def execute(self, context):
        self.start_operator()

        command_file = "temp_batch_exporter" if self.batch_export else "temp_exporter"
        CascadeurHandler().execute_csc_command(f"commands.externals.{command_file}")
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}


class CBB_OT_import_action_to_selected(OperatorBaseClass):
    """Imports the action from Cascadeur and apply to selected armature"""

    bl_idname = "cbb.import_cascadeur_action"
    bl_label = "Import Cascadeur Action"

    ao = None
    imported_objects = []

    @classmethod
    def poll(cls, context):
        return (
            context.active_object
            and context.selected_objects
            and context.active_object.type == "ARMATURE"
        )

    batch_export: bpy.props.BoolProperty(
        name="Import all scene",
        description="",
        default=False,
    )

    def modal(self, context, event):
        if event.type == "ESC":
            self._cleanup()
            return {"CANCELLED"}

        self.server_socket.run()

        if self.server_socket.client_socket:
            self.server_socket.send_message(get_csc_export_settings())
            data = self.server_socket.receive_message()
            if data:
                print(str(data))
                if not isinstance(data, list):
                    self.report({"ERROR"}, f"Unexpected response: {str(data)}")
                    addon_info.operation_completed = True
                    return {"CANCELLED"}

                for file in data:
                    objects = import_fbx(file)
                    self.imported_objects.extend(objects)
                    scene_name = os.path.splitext(os.path.basename(file))[0]
                    file_handling.delete_file(file)
                    actions = get_actions_from_armatures(objects)
                    apply_action(self.ao, actions[0], scene_name)
                delete_objects(self.imported_objects)

                self.ao.select_set(True)
                bpy.context.view_layer.objects.active = self.ao
                self.report({"INFO"}, "Finished")
                self._cleanup()
                return {"FINISHED"}

        return {"PASS_THROUGH"}

    def execute(self, context):
        self.start_operator()

        self.ao = bpy.context.active_object

        command_file = "temp_batch_exporter" if self.batch_export else "temp_exporter"
        CascadeurHandler().execute_csc_command(f"commands.externals.{command_file}")
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}


class CBB_OT_import_retarget_bake_to_selected(OperatorBaseClass):
    """Import animation from Cascadeur, retarget to selected armature, bake into current action."""

    bl_idname = "cbb.import_cascadeur_retarget_bake"
    bl_label = "Import + Retarget (Bake)"

    target_armature_obj: Optional[bpy.types.Object] = None
    imported_objects: list[bpy.types.Object] = []
    _actions_before: set[bpy.types.Action] = set()

    @classmethod
    def poll(cls, context):
        return (
            context.active_object
            and context.selected_objects
            and context.active_object.type == "ARMATURE"
        )

    def modal(self, context, event):
        if event.type == "ESC":
            self._cleanup()
            return {"CANCELLED"}

        self.server_socket.run()

        if self.server_socket.client_socket:
            self.server_socket.send_message(get_csc_export_settings())
            data = self.server_socket.receive_message()
            if data:
                if not isinstance(data, list):
                    self.report({"ERROR"}, f"Unexpected response: {str(data)}")
                    addon_info.operation_completed = True
                    return {"CANCELLED"}

                # Use first exported FBX as the animation source.
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
                    self.report({"ERROR"}, "No target armature selected.")
                    delete_objects(self.imported_objects)
                    self._cleanup()
                    return {"CANCELLED"}

                # Ensure we're baking into the currently active action on the target.
                target_action = _ensure_current_action(self.target_armature_obj)
                _clear_action(target_action)

                # Determine bake range from source action if present; otherwise use scene range.
                src_action = None
                if source_armature_obj.animation_data:
                    src_action = source_armature_obj.animation_data.action
                if src_action:
                    frame_start = int(src_action.frame_range[0])
                    frame_end = int(src_action.frame_range[1])
                else:
                    frame_start = int(context.scene.frame_start)
                    frame_end = int(context.scene.frame_end)

                try:
                    _retarget_and_bake_pose(
                        source_armature_obj=source_armature_obj,
                        target_armature_obj=self.target_armature_obj,
                        frame_start=frame_start,
                        frame_end=frame_end,
                    )
                except Exception as e:
                    self.report({"ERROR"}, f"Retarget/bake failed: {e}")
                    delete_objects(self.imported_objects)
                    self._cleanup()
                    return {"CANCELLED"}

                # Cleanup: delete imported objects and any new actions created by FBX import,
                # keeping only the target's current action.
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
        self.target_armature_obj = bpy.context.active_object
        self._actions_before = set(bpy.data.actions)

        CascadeurHandler().execute_csc_command("commands.externals.temp_exporter")
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}
