import csc


def command_name():
    return "External commands.Temp Exporter"


def run(scene):
    from .client_socket import ClientSocket
    from . import commons

    mp = csc.app.get_application()
    if mp is None:
        scene.error("Cascadeur application is not available (mp is None)")
        return

    scene_pr = mp.get_scene_manager().current_scene()
    if scene_pr is None:
        scene.error("No current scene is available in Cascadeur")
        return

    try:
        fbx_scene_loader = mp.get_tools_manager().get_tool("FbxSceneLoader").get_fbx_loader(scene_pr)
    except Exception as e:
        scene.error(f"Failed to acquire FbxSceneLoader: {type(e).__name__}: {e}")
        return

    export_path = commons.get_export_path(scene_pr.name())
    try:
        client = ClientSocket()
    except Exception as e:
        scene.error(f"Couldn't create socket. Error: {e}")
        return

    settings_dict: dict = client.receive_message()
    if not isinstance(settings_dict, dict):
        scene.error(f"Expected settings dict from Blender, got: {type(settings_dict).__name__}")
        try:
            client.send_message({"status": "ERROR", "error": "Invalid settings payload"})
        except Exception:
            pass
        client.close()
        return

    try:
        fbx_scene_loader.set_settings(commons.set_export_settings(settings_dict))
    except Exception as e:
        scene.error(f"Failed to apply FBX settings: {type(e).__name__}: {e}")
        try:
            client.send_message({"status": "ERROR", "error": f"Failed to apply FBX settings: {e}"})
        except Exception:
            pass
        client.close()
        return

    method_name = commons.resolve_export_method(settings_dict)
    if not hasattr(fbx_scene_loader, method_name):
        available = [n for n in dir(fbx_scene_loader) if n.startswith("export_")]
        msg = (
            f"Export method '{method_name}' not found on FbxLoader. "
            f"Available: {', '.join(available)}"
        )
        scene.error(msg)
        try:
            client.send_message({"status": "ERROR", "error": msg, "available_methods": available})
        except Exception:
            pass
        client.close()
        return

    export_method = getattr(fbx_scene_loader, method_name)
    try:
        export_method(export_path)
    except Exception as e:
        scene.error(f"Export failed via '{method_name}': {type(e).__name__}: {e}")
        try:
            client.send_message({"status": "ERROR", "error": f"Export failed: {e}", "method": method_name})
        except Exception:
            pass
        client.close()
        return

    scene.success(f"Exported via '{method_name}' to {export_path}")
    try:
        client.send_message([export_path])
    finally:
        client.close()
