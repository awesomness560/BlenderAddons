# Cascadeur ↔ Blender retarget bridge

This add-on started from **[Cascadeur Bridge for Blender](https://github.com/arcsikex/cascadeur_bridge)** by arcsikex. For general features, installation notes, Cascadeur version pairing, and troubleshooting, use that repository and its [README](https://github.com/arcsikex/cascadeur_bridge/blob/master/README.md).

**This fork is intentionally narrow:** you work with a **fully rigged character in Cascadeur** and a **separate, fully rigged character in Blender**, and you want to **pull animation from Cascadeur onto your Blender armature** with minimal friction. The UI is centered on **Retarget Configs**: pick a Blender armature, import from the open Cascadeur scene, retarget by matching bone names, bake into your current action, and optionally insert at a frame without wiping existing keys.

Upstream docs still apply for **preferences** (Cascadeur executable path, **Install Requirements**), socket port, and the need to keep Cascadeur bridge scripts in sync.

Install this add-on in Blender the same way as any local add-on (zip the add-on folder or point Blender at this directory), then enable it and run **Install Requirements** once.

## What to expect

- Bone names on the Cascadeur export and your Blender rig should **match** for the default copy-transforms retarget.
- Use the **Export / Import / Connection** sub-panel for FBX export method, import options, port, and saving settings.
- Legacy UI and operators from the original add-on are kept under `old_files/reference/` for reference only; they are not registered.

## License

Same as upstream ([GPL-3.0](https://github.com/arcsikex/cascadeur_bridge/blob/master/LICENSE)) unless you have changed it locally.
