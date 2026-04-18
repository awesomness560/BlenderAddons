# Reference copies (not loaded by the add-on)

Files in this folder are **snapshots of removed or legacy UI and operators** from earlier versions of the bridge. They are kept for human reference only.

- **`main_panel_legacy.py`** — Previous N-panel layout (export to Cascadeur, import scene/action, batch, etc.).
- **`settings_panel.py`**, **`socials.py`** — Old Settings / Information sub-panels (imports will not work from here; paths assume live `ui/` package).
- **`addon_properties_full.py`** — PropertyGroup including Blender→Cascadeur export options and `cbb_import_methods`.
- **`fbx_transfer_full.py`** — Operators such as `cbb.export_blender_fbx`, `cbb.import_cascadeur_fbx`, `cbb.import_cascadeur_action`, and the standalone retarget-bake button.

The active add-on only registers `ui/main_panel.py` (main + workflow settings) and the slim `operators/addon_properties.py` / `operators/fbx_transfer.py`.
