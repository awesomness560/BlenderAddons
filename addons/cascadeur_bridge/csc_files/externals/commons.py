import csc
import tempfile
import os


def resolve_export_method(settings_dict: dict) -> str:
    """
    When ``selected_interval`` is true, map generic export methods to the
    FbxLoader variants that export only the timeline's selected frame range.
    """
    method = settings_dict.get("export_method", "export_all_objects")
    if not settings_dict.get("selected_interval"):
        return method
    interval_map = {
        "export_all_objects": "export_scene_selected_frames",
        "export_joints": "export_joints_selected_frames",
        "export_scene_selected": "export_scene_selected_frames",
        "export_joints_selected": "export_joints_selected_frames",
    }
    return interval_map.get(method, method)


def set_export_settings(preferences: dict = {}) -> csc.fbx.FbxSettings:
    """
    Setting the fbx export settings in Cascadeur.

    :param dict preferences: Settings in key value pairs, defaults to {}
    :return csc.fbx.FbxSettings: FbxSettings object
    """
    settings = csc.fbx.FbxSettings()
    settings.mode = csc.fbx.FbxSettingsMode.Binary

    if preferences.get("euler_filter"):
        settings.apply_euler_filter = True
    else:
        settings.apply_euler_filter = False
    if preferences.get("up_axis") == "Z":
        settings.up_axis = csc.fbx.FbxSettingsAxis.Z
    else:
        settings.up_axis = csc.fbx.FbxSettingsAxis.Y
    if not preferences.get("bake_animation"):
        settings.bake_animation = False
    else:
        settings.bake_animation = True
    return settings


def get_export_path(scene_name: str) -> str:
    """
    FBX export path in the temp folder using the scene name.

    :param str scene_name: Name of the Cascadeur scene
    :return str: FBX export path
    """
    temp_dir = tempfile.gettempdir()
    file_name = scene_name.replace(".casc", "") + ".fbx"
    return os.path.join(temp_dir, file_name)
