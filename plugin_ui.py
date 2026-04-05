"""
DragDropLuaBlocks - Main UI Widget
Updated with Lua/LuaJIT selection and file save improvements
"""

import json
import time
import re
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QFileDialog,
    QComboBox, QTextEdit, QSplitter, QProgressBar,
    QTabWidget, QMessageBox, QListWidget, QListWidgetItem,
    QToolBox, QDialog, QFormLayout, QSpinBox, QCheckBox,
    QDialogButtonBox, QStyle, QApplication, QMenu
)
from PySide6.QtGui import QFont, QIcon, QTextCursor, QAction
from PySide6.QtCore import Qt, Signal, Slot, QTimer

from .block_components import (
    BlockScene, BlockProgrammingView, BlockLibraryWidget,
    CodePreviewWidget
)

from .enhanced_terminal import EnhancedLuaTerminal


class EngineSettingsDialog(QDialog):
    """Dialog for Lua engine settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lua Engine Settings")
        self.setModal(True)
        self.settings = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Only Lua option
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Lua"])
        self.engine_combo.setCurrentText("Lua")
        self.engine_combo.setEnabled(False)
        form_layout.addRow("Execution Engine:", self.engine_combo)
        
        # Memory limit
        self.memory_spin = QSpinBox()
        self.memory_spin.setRange(1, 1024)
        self.memory_spin.setValue(256)
        self.memory_spin.setSuffix(" MB")
        form_layout.addRow("Memory Limit:", self.memory_spin)
        
        # Debug mode
        self.debug_checkbox = QCheckBox("Enable debug mode")
        self.debug_checkbox.setChecked(False)
        form_layout.addRow("", self.debug_checkbox)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_settings(self):
        """Get settings from dialog"""
        return {
            'engine': 'lua',
            'memory_limit': self.memory_spin.value(),
            'enable_jit': False,
            'debug_mode': self.debug_checkbox.isChecked()
        }


class DragDropLuaBlocksWidget(QWidget):
    """Main widget for drag-and-drop Lua block programming"""
    
    def __init__(self, plugin_instance=None):
        super().__init__()
        self.plugin = plugin_instance
        self.current_file = None
        self.blocks = []
        self.connections = []
        self.engine_settings = {
            'engine': 'lua',
            'memory_limit': 256,
            'enable_jit': False,
            'debug_mode': False
        }
        
        self._setup_ui()
        self._connect_signals()
        
        # Set window icon if available
        if plugin_instance and hasattr(plugin_instance, 'icon') and plugin_instance.icon:
            self.setWindowIcon(plugin_instance.icon)
    
    def _setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Title bar with engine indicator
        title_layout = QHBoxLayout()
        title_label = QLabel("Drag-and-Drop Lua Blocks")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50;")
        title_layout.addWidget(title_label)
        
        # Engine indicator
        self.engine_label = QLabel("Engine: Lua")
        self.engine_label.setStyleSheet("color: #3498db; font-weight: bold;")
        title_layout.addWidget(self.engine_label)
        
        title_layout.addStretch()
        
        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #e74c3c; font-size: 24px;")
        title_layout.addWidget(self.status_indicator)
        main_layout.addLayout(title_layout)
        
        # Control toolbar
        toolbar_layout = QHBoxLayout()
        
        # File operations
        self.new_btn = QPushButton("New")
        self.new_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        self.open_btn = QPushButton("Open")
        self.open_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.save_btn = QPushButton("Save")
        self.save_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_as_btn = QPushButton("Save As")
        self.save_as_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_DriveHDIcon))
        
        # Code operations
        self.generate_btn = QPushButton("Generate Code")
        self.generate_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.export_lua_btn = QPushButton("Export Lua File")
        self.export_lua_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_CommandLink))
        
        # Engine settings
        self.engine_btn = QPushButton("Engine Settings")
        self.engine_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # Run buttons
        self.run_btn = QPushButton("Run")
        self.run_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.run_btn.clicked.connect(self._run_lua_code)
        
        self.run_settings_btn = QPushButton("Settings")
        self.run_settings_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogContentsView))
        self.run_settings_btn.clicked.connect(self._show_run_options)
        
        toolbar_layout.addWidget(self.new_btn)
        toolbar_layout.addWidget(self.open_btn)
        toolbar_layout.addWidget(self.save_btn)
        toolbar_layout.addWidget(self.save_as_btn)
        toolbar_layout.addWidget(self.generate_btn)
        toolbar_layout.addWidget(self.export_lua_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.engine_btn)
        toolbar_layout.addWidget(self.run_btn)
        toolbar_layout.addWidget(self.run_settings_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        # ========== MAIN CONTENT SPLITTER ==========
        main_splitter = QSplitter(Qt.Horizontal)
        
        # ========== LEFT PANEL: Block Library ==========
        self.library_widget = BlockLibraryWidget()
        main_splitter.addWidget(self.library_widget)
        
        # ========== CENTER PANEL: Block Canvas ==========
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        # Canvas toolbar
        canvas_toolbar = QHBoxLayout()
        self.zoom_in_btn = QPushButton("Zoom In (+)")
        self.zoom_out_btn = QPushButton("Zoom Out (-)")
        self.fit_view_btn = QPushButton("Fit View")
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_TrashIcon))
        
        canvas_toolbar.addWidget(self.zoom_in_btn)
        canvas_toolbar.addWidget(self.zoom_out_btn)
        canvas_toolbar.addWidget(self.fit_view_btn)
        canvas_toolbar.addStretch()
        canvas_toolbar.addWidget(self.delete_btn)
        
        center_layout.addLayout(canvas_toolbar)
        
        # Block scene and view
        self.block_scene = BlockScene()
        self.block_view = BlockProgrammingView(self.block_scene)
        center_layout.addWidget(self.block_view)
        
        main_splitter.addWidget(center_widget)
        
        # ========== RIGHT PANEL: Terminal + Code Preview + Project Tree ==========
        self.right_tabs = QTabWidget()
        
        # Tab 1: Interactive Terminal
        terminal_tab = QWidget()
        terminal_layout = QVBoxLayout(terminal_tab)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        
        self.terminal = EnhancedLuaTerminal(parent=self, engine_type="lua")
        self.terminal.command_executed.connect(self.execute_terminal_command)
        terminal_layout.addWidget(self.terminal)
        
        self.right_tabs.addTab(terminal_tab, "Terminal")
        
        # Tab 2: Code Preview
        self.code_preview = CodePreviewWidget()
        self.right_tabs.addTab(self.code_preview, "Lua Code")
        
        # Tab 3: Project Tree
        project_tab = QWidget()
        project_layout = QVBoxLayout(project_tab)
        
        self.project_tree = QListWidget()
        self.project_tree.setMaximumHeight(200)
        project_layout.addWidget(self.project_tree)
        
        self.file_info_label = QLabel("No project loaded")
        self.file_info_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        project_layout.addWidget(self.file_info_label)
        
        project_layout.addStretch()
        self.right_tabs.addTab(project_tab, "Project")
        
        main_splitter.addWidget(self.right_tabs)
        
        # Set splitter sizes
        main_splitter.setSizes([200, 500, 350])
        main_layout.addWidget(main_splitter)
        
        # ========== BOTTOM PANEL: Build Output ==========
        output_group = QGroupBox("Build Output")
        output_layout = QVBoxLayout()
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(120)
        self.output_text.setFont(QFont("Courier New", 9))
        output_layout.addWidget(self.output_text)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)
        
        # ========== PROGRESS BAR ==========
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # ========== STATUS BAR ==========
        self.status_label = QLabel("Ready to create Lua programs with drag-and-drop blocks")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        main_layout.addWidget(self.status_label)
    
    def create_tools_panel(self):
        """Create tools panel with enhanced terminal and output"""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Output console
        output_group = QGroupBox("Build Output")
        output_layout = QVBoxLayout()
        
        self.output_text_alt = QTextEdit()
        self.output_text_alt.setReadOnly(True)
        self.output_text_alt.setMaximumHeight(150)
        self.output_text_alt.setFont(QFont("Courier New", 9))
        output_layout.addWidget(self.output_text_alt)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Terminal
        console_group = QGroupBox("Interactive Terminal")
        console_layout = QVBoxLayout()
        
        self.terminal_alt = EnhancedLuaTerminal(parent=self, engine_type="lua")
        self.terminal_alt.command_executed.connect(self.execute_terminal_command)
        console_layout.addWidget(self.terminal_alt)
        
        console_group.setLayout(console_layout)
        layout.addWidget(console_group)
        
        panel.setLayout(layout)
        return panel
    
    def execute_terminal_command(self, command: str):
        """Execute command from enhanced terminal with return value capture"""
        start_time = time.time()
        
        # Use standard Lua
        bridge = None
        
        try:
            from plugins.libs.lua.lua_bridge import get_lua_bridge
            bridge = get_lua_bridge()
        except ImportError as e:
            print(f"Lua bridge import error: {e}")
            self.terminal.append_error("No Lua engine available!")
            return
        
        try:
            lua_state = bridge.init()
            if not lua_state:
                self.terminal.append_error("Failed to initialize Lua state")
                return
            
            try:
                escaped_command = command.replace('\\', '\\\\').replace('`', '\\`')
                
                wrapper = f"""
                local _old_print = print
                local _output_lines = {{}}
                print = function(...)
                    local args = {{...}}
                    local line = table.concat(args, "\\t")
                    table.insert(_output_lines, line)
                    _old_print(...)
                end
                
                local _return_value = nil
                local ok, err = pcall(function()
                    local chunk = load([==[{escaped_command}]==])
                    if chunk then
                        local results = {{chunk()}}
                        if #results > 0 then
                            _return_value = results
                        end
                    end
                end)
                
                print = _old_print
                
                if not ok then
                    return false, tostring(err)
                else
                    _G["_term_output"] = _output_lines
                    _G["_term_return"] = _return_value
                    return true
                end
                """
                
                success = bridge.execute_script(lua_state, wrapper)
                
                if success:
                    bridge.execute_script(lua_state, """
                    for i, line in ipairs(_G["_term_output"] or {{}}) do
                        _G["_tline_"..i] = line
                    end
                    """)
                    
                    for i in range(1, 1000):
                        try:
                            line = bridge.get_global_string(lua_state, f"_tline_{i}")
                            if line:
                                self.terminal.append_output(line)
                            else:
                                break
                        except:
                            break
                    
                    try:
                        bridge.execute_script(lua_state, """
                        local rv = _G["_term_return"]
                        if type(rv) == 'table' then
                            local result = {}
                            for i, v in ipairs(rv) do
                                if type(v) == 'table' then
                                    result[i] = 'table'
                                elseif type(v) == 'string' then
                                    result[i] = '"' .. v .. '"'
                                else
                                    result[i] = tostring(v)
                                end
                            end
                            _term_return_str = table.concat(result, ', ')
                        else
                            _term_return_str = tostring(rv)
                        end
                        """)
                        return_val = bridge.get_global_string(lua_state, "_term_return_str")
                        if return_val and return_val != "nil" and return_val != "":
                            self.terminal.append_return_value(return_val)
                    except:
                        pass
                    
                else:
                    error = bridge.get_last_error(lua_state)
                    line_match = re.search(r':(\d+):', error)
                    line_num = int(line_match.group(1)) if line_match else None
                    self.terminal.append_error(error, line_num)
                
                elapsed = time.time() - start_time
                self.terminal.append_timing(elapsed)
                
            finally:
                bridge.close(lua_state)
                
        except Exception as e:
            self.terminal.append_error(f"Execution error: {str(e)}")
    
    def _connect_signals(self):
        """Connect signals and slots"""
        self.new_btn.clicked.connect(self._new_project)
        self.open_btn.clicked.connect(self._open_project)
        self.save_btn.clicked.connect(self._save_project)
        self.save_as_btn.clicked.connect(self._save_as_project)
        
        self.generate_btn.clicked.connect(self._generate_lua_code)
        self.export_lua_btn.clicked.connect(self._export_lua_file)
        self.engine_btn.clicked.connect(self._open_engine_settings)
        
        self.library_widget.block_selected.connect(self._add_block_from_library)
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        self.fit_view_btn.clicked.connect(self._fit_view)
        self.delete_btn.clicked.connect(self._delete_selected)
        
        self.block_scene.block_added.connect(self._on_block_added)
        self.block_scene.block_removed.connect(self._on_block_removed)
    
    def _open_engine_settings(self):
        """Open engine settings dialog"""
        dialog = EngineSettingsDialog(self)
        if dialog.exec():
            self.engine_settings = dialog.get_settings()
            engine_name = self.engine_settings['engine'].upper()
            self.engine_label.setText(f"Engine: {engine_name}")
            self.status_label.setText(f"Engine set to {engine_name}")
    
    def _new_project(self):
        """Create new project"""
        if self.blocks:
            reply = QMessageBox.question(
                self, "New Project",
                "Create new project? Unsaved changes will be lost.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        self.block_scene.clear()
        self.blocks.clear()
        self.connections.clear()
        self.current_file = None
        
        if hasattr(self, 'project_tree'):
            self.project_tree.clear()
        if hasattr(self, 'code_preview'):
            self.code_preview.clear()
        if hasattr(self, 'file_info_label'):
            self.file_info_label.setText("New project")
        
        self.status_label.setText("New project created")
        self.status_indicator.setStyleSheet("color: #2ecc71; font-size: 24px;")
    
    def _open_project(self):
        """Open project from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Block Project", "",
            "Block Projects (*.blockproj);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                self.block_scene.clear()
                self.blocks.clear()
                self.connections.clear()
                
                for block_data in data.get('blocks', []):
                    from .block_components import LuaBlock
                    block = LuaBlock.from_dict(block_data)
                    self.block_scene.addItem(block)
                    self.blocks.append(block)
                
                if 'engine_settings' in data:
                    self.engine_settings = data['engine_settings']
                    engine_name = self.engine_settings.get('engine', 'lua').upper()
                    self.engine_label.setText(f"Engine: {engine_name}")
                
                self._update_project_tree()
                self.current_file = Path(file_path)
                self.file_info_label.setText(f"Loaded: {self.current_file.name}")
                self.status_label.setText(f"Project loaded: {self.current_file.name}")
                self.status_indicator.setStyleSheet("color: #2ecc71; font-size: 24px;")
                
                self._generate_lua_code(preview_only=True)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load project: {str(e)}")
    
    def _save_project(self):
        """Save project to current file"""
        if not self.current_file:
            self._save_as_project()
        else:
            self._save_to_file(self.current_file)
    
    def _save_as_project(self):
        """Save project to new file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Block Project", "",
            "Block Projects (*.blockproj);;All Files (*)"
        )
        if file_path:
            self.current_file = Path(file_path)
            self._save_to_file(self.current_file)
    
    def _save_to_file(self, file_path: Path):
        """Save project data to file"""
        try:
            blocks_data = []
            for item in self.block_scene.items():
                from .block_components import LuaBlock
                if isinstance(item, LuaBlock):
                    blocks_data.append(item.to_dict())
            
            project_data = {
                'version': '1.0',
                'blocks': blocks_data,
                'engine_settings': self.engine_settings,
                'metadata': {
                    'name': file_path.stem,
                    'created': '2026-02-01',
                    'modified': '2026-02-01'
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(project_data, f, indent=2)
            
            self.file_info_label.setText(f"Saved: {file_path.name}")
            self.status_label.setText(f"Project saved: {file_path.name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project: {str(e)}")
    
    def _export_lua_file(self):
        """Export generated Lua code to file"""
        code = self.code_preview.toPlainText()
        
        if not code.strip():
            QMessageBox.warning(self, "No Code", "Generate Lua code first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Lua File", "",
            "Lua Files (*.lua);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                self.status_label.setText(f"Lua code exported to: {Path(file_path).name}")
                QMessageBox.information(self, "Success", f"Lua code exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export Lua code: {str(e)}")
    
    def _add_block_from_library(self, block_data: dict):
        """Add block from library to scene"""
        block = self.block_scene.add_block(block_data)
        if block:
            self.blocks.append(block)
            self._update_project_tree()
    
    def _on_block_added(self, block):
        self._update_project_tree()
    
    def _on_block_removed(self, block):
        if block in self.blocks:
            self.blocks.remove(block)
        self._update_project_tree()
    
    def _update_project_tree(self):
        """Update project tree view"""
        if hasattr(self, 'project_tree'):
            self.project_tree.clear()
            for block in self.blocks:
                item = QListWidgetItem(f"▢ {block.title} (#{block.block_id})")
                item.block = block
                self.project_tree.addItem(item)
    
    def _zoom_in(self):
        self.block_view.scale(1.2, 1.2)
    
    def _zoom_out(self):
        self.block_view.scale(0.8, 0.8)
    
    def _fit_view(self):
        self.block_view.fitInView(self.block_scene.itemsBoundingRect(), Qt.KeepAspectRatio)
    
    def _delete_selected(self):
        for item in self.block_scene.selectedItems():
            from .block_components import LuaBlock
            if isinstance(item, LuaBlock):
                item.block_deleted.emit(item)
    
    def _generate_lua_code(self, preview_only=False):
        """Generate Lua code from blocks"""
        try:
            entry_blocks = []
            for block in self.blocks:
                if hasattr(block, 'block_type') and block.block_type == 'event':
                    entry_blocks.append(block)
            
            if not entry_blocks and not preview_only:
                QMessageBox.warning(self, "No Entry Points", 
                                  "Add an 'On Start' or similar event block to generate code.")
                return
            
            lua_code = self._generate_complete_code()
            
            if hasattr(self, 'code_preview'):
                self.code_preview.update_code(lua_code)
                if hasattr(self, 'right_tabs'):
                    self.right_tabs.setCurrentIndex(1)
            
            self.status_label.setText("Lua code generated")
            
            if not preview_only:
                temp_dir = Path.home() / ".qha" / "temp_lua"
                temp_dir.mkdir(parents=True, exist_ok=True)
                temp_file = temp_dir / f"generated_{self._get_project_name()}.lua"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(lua_code)
                self.status_label.setText(f"Lua code generated and saved to temp file")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate Lua code: {str(e)}")
    
    def _generate_complete_code(self):
        """Generate complete Lua code from ALL blocks with proper structure"""
        import datetime
        
        project_name = self._get_project_name()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        engine = self.engine_settings['engine'].upper()
        
        all_blocks = []
        event_blocks = []
        variable_declarations = []
        function_definitions = []
        control_blocks = []
        math_blocks = []
        quantum_blocks = []
        
        for block in self.blocks:
            if not hasattr(block, 'block_type'):
                continue
                
            all_blocks.append(block)
            
            if block.block_type == 'event':
                event_blocks.append(block)
            elif block.block_type == 'variable':
                variable_declarations.append(block)
            elif block.block_type == 'function':
                function_definitions.append(block)
            elif block.block_type == 'control':
                control_blocks.append(block)
            elif block.block_type == 'operator' or 'Math' in getattr(block, 'title', ''):
                math_blocks.append(block)
            elif block.block_type == 'action' or 'Quantum' in getattr(block, 'title', ''):
                quantum_blocks.append(block)
        
        code_lines = []
        
        # 1. Header comments
        code_lines.append('-- Generated by Drag-and-Drop Lua Blocks Plugin')
        code_lines.append(f'-- Project: {project_name}')
        code_lines.append(f'-- Engine: {engine}')
        code_lines.append(f'-- Generated: {timestamp}')
        code_lines.append(f'-- Memory Limit: {self.engine_settings["memory_limit"]}MB')
        code_lines.append(f'-- Debug: {"Enabled" if self.engine_settings["debug_mode"] else "Disabled"}')
        code_lines.append(f'-- Blocks: {len(all_blocks)} total ({len(event_blocks)} events, {len(variable_declarations)} vars, {len(function_definitions)} funcs, {len(control_blocks)} controls, {len(math_blocks)} math, {len(quantum_blocks)} quantum)')
        code_lines.append('')
        
        # 2. Print header
        code_lines.append(f'print("=== {project_name} ===")')
        code_lines.append(f'print("Engine: {engine}")')
        code_lines.append(f'print("Generated: {timestamp}")')
        code_lines.append(f'print("Total blocks: {len(all_blocks)}")')
        code_lines.append('')
        
        # 3. Variable declarations
        if variable_declarations:
            code_lines.append('-- VARIABLE DECLARATIONS --')
            for block in variable_declarations:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code()
                    if block_code and block_code.strip():
                        code_lines.append(block_code.rstrip())
            code_lines.append('')
        
        # 4. Function definitions
        if function_definitions:
            code_lines.append('-- FUNCTION DEFINITIONS --')
            for block in function_definitions:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code()
                    if block_code and block_code.strip():
                        code_lines.append(block_code.rstrip())
            code_lines.append('')
        
        # 5. Main execution
        code_lines.append('-- MAIN EXECUTION --')
        code_lines.append('local function main()')
        
        indent = '    '
        
        if event_blocks:
            code_lines.append(f'{indent}-- EVENT HANDLERS --')
            for block in event_blocks:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code(1)
                    if block_code and block_code.strip():
                        for line in block_code.split('\n'):
                            if line.strip():
                                code_lines.append(line)
            code_lines.append('')
        
        if control_blocks:
            code_lines.append(f'{indent}-- CONTROL STRUCTURES --')
            for block in control_blocks:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code(1)
                    if block_code and block_code.strip():
                        for line in block_code.split('\n'):
                            if line.strip():
                                code_lines.append(line)
            code_lines.append('')
        
        if math_blocks:
            code_lines.append(f'{indent}-- MATH OPERATIONS --')
            for block in math_blocks:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code(1)
                    if block_code and block_code.strip():
                        for line in block_code.split('\n'):
                            if line.strip():
                                code_lines.append(line)
            code_lines.append('')
        
        if quantum_blocks:
            code_lines.append(f'{indent}-- QUANTUM OPERATIONS --')
            for block in quantum_blocks:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code(1)
                    if block_code and block_code.strip():
                        for line in block_code.split('\n'):
                            if line.strip():
                                code_lines.append(line)
            code_lines.append('')
        
        action_blocks = [b for b in self.blocks if hasattr(b, 'block_type') and b.block_type == 'action']
        if action_blocks:
            code_lines.append(f'{indent}-- ACTIONS --')
            for block in action_blocks:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code(1)
                    if block_code and block_code.strip():
                        for line in block_code.split('\n'):
                            if line.strip():
                                code_lines.append(line)
            code_lines.append('')
        
        code_lines.append('end')
        code_lines.append('')
        
        # 6. Error handling wrapper
        code_lines.append('-- ERROR HANDLING WRAPPER --')
        code_lines.append('local success, err = pcall(main)')
        code_lines.append('if not success then')
        code_lines.append('    print("")')
        code_lines.append('    print("=== ERROR ===")')
        code_lines.append('    print("Error during execution:", err)')
        code_lines.append('    ')
        code_lines.append('    if string.find(err, "attempt to perform arithmetic") then')
        code_lines.append('        print("Hint: Check your math operations for type mismatches")')
        code_lines.append('    elseif string.find(err, "attempt to call") then')
        code_lines.append('        print("Hint: Make sure you\\\'re calling functions that exist")')
        code_lines.append('    elseif string.find(err, "not enough memory") then')
        code_lines.append('        print("Hint: Try increasing memory limit in engine settings")')
        code_lines.append('    elseif string.find(err, "syntax error") then')
        code_lines.append('        print("Hint: Check for missing parentheses, brackets, or quotes")')
        code_lines.append('    end')
        code_lines.append('    ')
        code_lines.append('    print("")')
        code_lines.append('    print("Stack trace:")')
        code_lines.append('    debug.traceback(err, 2)')
        code_lines.append('else')
        code_lines.append('    print("")')
        code_lines.append('    print("=== SUCCESS ===")')
        code_lines.append('    print("Execution completed successfully")')
        code_lines.append('end')
        code_lines.append('')
        code_lines.append('print("")')
        code_lines.append('print("=== End of Program ===")')
        code_lines.append('')
        code_lines.append('if success then')
        code_lines.append('    return 0')
        code_lines.append('else')
        code_lines.append('    return 1')
        code_lines.append('end')
        
        return '\n'.join(code_lines)

    def _get_project_name(self):
        if self.current_file:
            return self.current_file.stem
        return "UntitledProject"
    
    def _run_lua_code(self, engine_type=None):
        """Run the generated Lua code with standard Lua engine"""
        code = self.code_preview.toPlainText()
        
        if not code.strip():
            QMessageBox.warning(self, "No Code", "Generate Lua code first.")
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("Executing with Lua...")
            
            QTimer.singleShot(100, lambda: self._execute_with_lua(code))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize Lua engine: {str(e)}")
            self.progress_bar.setVisible(False)
    
    def _execute_with_lua(self, code):
        """Execute code with standard Lua"""
        try:
            from plugins.libs.lua.lua_bridge import get_lua_bridge
            bridge = get_lua_bridge()
            
            lua_state = bridge.init()
            if not lua_state:
                raise RuntimeError("Failed to initialize Lua state")
            
            if self.engine_settings['memory_limit'] > 0:
                memory_code = f"""
local limit = {self.engine_settings['memory_limit']} * 1024 * 1024
print(string.format("Memory limit: %.1f MB", limit / (1024*1024)))
"""
                try:
                    bridge.execute_script(lua_state, memory_code)
                except:
                    pass
            
            success = bridge.execute_script(lua_state, code)
            
            if success:
                self.status_label.setText("Lua execution completed successfully")
                QMessageBox.information(self, "Success", "Lua code executed successfully!")
            else:
                error_msg = self._get_lua_error(bridge, lua_state)
                self.status_label.setText("Lua execution failed")
                QMessageBox.critical(self, "Lua Error", f"Execution failed:\n{error_msg}")
            
            bridge.cleanup(lua_state)
            
        except ImportError as e:
            print(f"Lua bridge not available: {e}")
            self._run_in_demo_mode(code, "Lua")
        except Exception as e:
            self.status_label.setText(f"Execution error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to execute Lua code:\n{str(e)}")
        finally:
            self.progress_bar.setVisible(False)
    
    def _get_lua_error(self, bridge, lua_state):
        """Get error message from Lua stack"""
        try:
            if hasattr(bridge.lib, 'lua_tolstring'):
                err_ptr = bridge.lib.lua_tolstring(lua_state, -1, None)
                if err_ptr:
                    import ctypes
                    return ctypes.string_at(err_ptr).decode('utf-8', errors='ignore')
        except:
            pass
        return "Unknown error"
    
    def _run_in_demo_mode(self, code, engine_name):
        """Run in demo mode when Lua engine is not available"""
        demo_dialog = QDialog(self)
        demo_dialog.setWindowTitle(f"{engine_name} Demo Mode")
        demo_dialog.setModal(True)
        demo_dialog.resize(600, 400)
        
        layout = QVBoxLayout(demo_dialog)
        
        info_label = QLabel(f"{engine_name} bridge not available. Running in demo mode.")
        info_label.setStyleSheet("color: #e67e22; font-weight: bold;")
        layout.addWidget(info_label)
        
        code_text = QTextEdit()
        code_text.setPlainText(code)
        code_text.setReadOnly(True)
        code_text.setFont(QFont("Consolas", 10))
        layout.addWidget(code_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(demo_dialog.accept)
        layout.addWidget(close_btn)
        
        demo_dialog.exec()
        self.status_label.setText("Code displayed in demo mode")
    
    def _show_run_options(self):
        """Show run options menu"""
        menu = QMenu(self)
        
        run_lua_action = menu.addAction("Run with Lua")
        run_lua_action.triggered.connect(lambda: self._run_lua_code('lua'))
        
        menu.addSeparator()
        
        run_debug_action = menu.addAction("Run with Debug Mode")
        run_debug_action.triggered.connect(lambda: self._run_lua_code('debug'))
        
        menu.exec(self.run_settings_btn.mapToGlobal(self.run_settings_btn.rect().bottomLeft()))