if "bpy" not in locals():
    from . import main_panel
else:
    import importlib

    importlib.reload(main_panel)

import bpy

classes = [
    main_panel.CBB_PT_parent_panel,
    main_panel.CBB_PT_workflow_settings,
]
