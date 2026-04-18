if "bpy" not in locals():
    from . import fbx_transfer
    from . import csc_ops
    from . import addon_properties
else:
    import importlib

    importlib.reload(fbx_transfer)
    importlib.reload(csc_ops)
    importlib.reload(addon_properties)

classes = [
    fbx_transfer.CBB_OT_retarget_config_add,
    fbx_transfer.CBB_OT_retarget_config_remove,
    fbx_transfer.CBB_OT_import_retarget_bake_config,
    csc_ops.CBB_OT_start_cascadeur,
    csc_ops.CBB_OT_install_required_files,
    addon_properties.CBB_OT_save_fbx_settings,
    addon_properties.CBB_OT_reset_fbx_settings,
    addon_properties.CBB_OT_save_port_number,
]
