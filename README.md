# Drag-and-Drop Lua Blocks

Visual programming environment for Lua with drag-and-drop blocks

## Features
- Feature 1
- Feature 2
- Feature 3

## Installation
1. Download the plugin ZIP file
2. In Quantum Analyzer Helper, go to Plugins → Import Plugin...
3. Select the ZIP file
4. The plugin will appear in the Plugins menu

## Usage
1. Open the plugin from the Plugins menu
2. Use the interface to interact with the plugin
3. Configure settings as needed

## Configuration
Edit the `manifest.json` file to change plugin settings.

## Development
This plugin was created with the Plugin Creator tool.

### Key Changes
1. **Centralized Python Utilities**: All shared Python code moved to `plugins.libs.python_utils`
2. **Unified Plugin Management**: All plugin-related utilities in `plugins.libs`
3. **Better Separation**: Core libraries vs. individual plugins
4. **Easier Maintenance**: Shared code updates affect all plugins

## Plugin Structure

### Core Plugin Files in `plugins.libs/`

| File | Purpose |
|------|---------|
| `base_plugin.py` | Abstract base classes for all plugins |
| `lua_bridge.py` | Lua 5.4+ integration bridge |
| `luajit_bridge.py` | LuaJIT (Lua 5.1) integration bridge |
| `plugin_manager.py` | Main plugin lifecycle management |
| `import_manager.py` | Plugin import/export functionality |
| `import_dialog.py` | UI for plugin import operations |
| `one_click_importer.py` | Simplified plugin installation |
| `debug_plugin_import.py` | Debug utilities for plugin loading |

### Plugin Manifest (`manifest.json`)
```json
{
  "name": "Drag-and-Drop Lua Blocks",
  "id": "drag_and_drop_lua_blocks",
  "version": "1.0.0",
  "author": "Acxel Orozco",
  "description": "Visual programming environment for Lua with drag-and-drop blocks",
  "type": "python",
  "category": "development",
  "main": "__init__.py"
}
Version: 1.0.0
Author: Acxel Orozco
Created: 2026-02-05
