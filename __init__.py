"""
DragDropLuaBlocks - Visual Programming Environment for Lua
This file is part of Quantum Analysis Helper.
Quantum Analysis Helper is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Quantum Analysis Helper is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Copyright (C) [2026] Acxel David Orozco Baldomero
"""
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QIcon
from PySide6.QtCore import QObject

from plugins.libs.plugin_manager import PluginInfo


class DragDropLuaBlocks(QObject):
    """Main plugin class for drag-and-drop Lua block programming"""
    
    def __init__(self, plugin_info: PluginInfo):
        super().__init__()
        self.plugin_info = plugin_info
        self.ui_widget = None
        self.icon = None
        
        # Load icon if available
        plugin_dir = Path(__file__).parent
        icon_path = plugin_dir / "icon.png"
        if icon_path.exists():
            self.icon = QIcon(str(icon_path))
    
    def initialize(self):
        """Initialize the plugin"""
        try:
            logging.info(f"Initializing {self.plugin_info.name} version: {self.plugin_info.version}")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize plugin: {e}")
            return False
    
    def get_widget(self) -> Optional[QWidget]:
        """Get the main UI widget for this plugin"""
        if self.ui_widget is None:
            try:
                from .plugin_ui import DragDropLuaBlocksWidget
                self.ui_widget = DragDropLuaBlocksWidget(self)
            except Exception as e:
                logging.error(f"Failed to initialize widget: {e}")
                return None
        return self.ui_widget
    
    def get_menu_action(self):
        """Get menu action for this plugin"""
        from PySide6.QtGui import QAction
        
        action = QAction(self.plugin_info.name, None)
        if self.icon:
            action.setIcon(self.icon)
        action.triggered.connect(self.open_editor)
        return action
    
    def open_editor(self):
        """Open the block editor widget"""
        widget = self.get_widget()
        if widget:
            return widget
        return None
    
    def cleanup(self):
        """Cleanup resources"""
        if self.ui_widget:
            self.ui_widget.deleteLater()
            self.ui_widget = None


# Plugin factory function (required by plugin manager)
Plugin = DragDropLuaBlocks