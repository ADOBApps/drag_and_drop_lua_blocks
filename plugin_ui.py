"""
DragDropLuaBlocks - Main UI Widget
Updated with Lua/LuaJIT selection and file save improvements
"""

import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QFileDialog,
    QComboBox, QTextEdit, QSplitter, QProgressBar,
    QTabWidget, QMessageBox, QListWidget, QListWidgetItem,
    QToolBox, QDialog, QFormLayout, QSpinBox, QCheckBox,
    QDialogButtonBox, QStyle, QApplication
)
from PySide6.QtGui import QFont, QIcon, QTextCursor
from PySide6.QtCore import Qt, Signal, Slot, QTimer

from .block_components import (
    BlockScene, BlockProgrammingView, BlockLibraryWidget,
    CodePreviewWidget
)


class EngineSettingsDialog(QDialog):
    """Dialog for Lua/LuaJIT engine settings"""
    
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
        
        # Engine selection
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Lua", "LuaJIT"])
        self.engine_combo.setCurrentText("Lua")
        form_layout.addRow("Execution Engine:", self.engine_combo)
        
        # Memory limit (for LuaJIT)
        self.memory_spin = QSpinBox()
        self.memory_spin.setRange(1, 1024)  # MB
        self.memory_spin.setValue(256)
        self.memory_spin.setSuffix(" MB")
        form_layout.addRow("Memory Limit:", self.memory_spin)
        
        # Enable JIT compilation
        self.jit_checkbox = QCheckBox("Enable JIT compilation")
        self.jit_checkbox.setChecked(True)
        form_layout.addRow("", self.jit_checkbox)
        
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
            'engine': self.engine_combo.currentText().lower(),
            'memory_limit': self.memory_spin.value(),
            'enable_jit': self.jit_checkbox.isChecked(),
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
            'enable_jit': True,
            'debug_mode': False
        }
        
        self._setup_ui()
        self._connect_signals()
        
        # Set window icon if available
        if plugin_instance and plugin_instance.icon:
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
        self.new_btn.setIcon(
            QApplication.style().standardIcon(QStyle.SP_FileIcon)
        )
        self.open_btn = QPushButton("Open")
        self.open_btn.setIcon(
            QApplication.style().standardIcon(QStyle.SP_DirOpenIcon)
        )
        self.save_btn = QPushButton("Save")
        self.save_btn.setIcon(
            QApplication.style().standardIcon(QStyle.SP_DialogSaveButton)
        )
        self.save_as_btn = QPushButton("Save As")
        self.save_as_btn.setIcon(
            QApplication.style().standardIcon(QStyle.SP_DriveHDIcon)
        )
        
        # Code operations
        self.generate_btn = QPushButton("Generate Code")
        self.generate_btn.setIcon(
            QApplication.style().standardIcon(QStyle.SP_TitleBarMaxButton)
        )
        self.export_lua_btn = QPushButton("Export Lua File")
        self.export_lua_btn.setIcon(
            QApplication.style().standardIcon(QStyle.SP_CommandLink)
        )
        
        # Engine settings
        self.engine_btn = QPushButton("Engine Settings")
        self.engine_btn.setIcon(
            QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
        )
        
        # Run buttons with dropdown
        self.run_btn = QPushButton("Run")
        self.run_btn.setIcon(
            QApplication.style().standardIcon(QStyle.SP_MediaPlay)
        )
        self.run_btn.clicked.connect(self._run_lua_code)  # Will use default engine

        # Create a separate settings button if you want dropdown functionality
        self.run_settings_btn = QPushButton("Settings")
        self.run_settings_btn.setIcon(
            QApplication.style().standardIcon(QStyle.SP_FileDialogContentsView)
        )
        self.run_settings_btn.clicked.connect(self._show_run_options)

        # In the toolbar layout, use:
        
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
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Block Library
        self.library_widget = BlockLibraryWidget()
        splitter.addWidget(self.library_widget)
        
        # Center panel - Block Canvas
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        # Canvas toolbar
        canvas_toolbar = QHBoxLayout()
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_out_btn = QPushButton("-")
        self.fit_view_btn = QPushButton("Fit")
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setIcon(
            QApplication.style().standardIcon(QStyle.SP_TrashIcon)
        )
        
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
        
        splitter.addWidget(center_widget)
        
        # Right panel - Properties and Preview
        self.right_tabs = QTabWidget()
        
        # Code preview tab
        self.code_preview = CodePreviewWidget()
        self.right_tabs.addTab(self.code_preview, "Lua Code")
        
        # Project tree tab
        project_tab = QWidget()
        project_layout = QVBoxLayout(project_tab)
        
        self.project_tree = QListWidget()
        self.project_tree.setMaximumHeight(200)
        project_layout.addWidget(self.project_tree)
        
        # File info
        self.file_info_label = QLabel("No project loaded")
        self.file_info_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        project_layout.addWidget(self.file_info_label)
        
        project_layout.addStretch()
        self.right_tabs.addTab(project_tab, "Project")
        
        splitter.addWidget(self.right_tabs)
        
        # Set splitter sizes
        splitter.setSizes([200, 600, 200])
        main_layout.addWidget(splitter)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Status bar
        self.status_label = QLabel("Ready to create Lua programs with drag-and-drop blocks")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        main_layout.addWidget(self.status_label)
    
    def _create_run_menu(self):
        """Create run button dropdown menu"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        menu = QMenu()
        
        run_lua_action = QAction("Run with Lua", self)
        run_lua_action.triggered.connect(lambda: self._run_lua_code('lua'))
        
        run_luajit_action = QAction("Run with LuaJIT", self)
        run_luajit_action.triggered.connect(lambda: self._run_lua_code('luajit'))
        
        run_debug_action = QAction("Run with Debug", self)
        run_debug_action.triggered.connect(lambda: self._run_lua_code('debug'))
        
        menu.addAction(run_lua_action)
        menu.addAction(run_luajit_action)
        menu.addSeparator()
        menu.addAction(run_debug_action)
        
        return menu
    
    def _connect_signals(self):
        """Connect signals and slots"""
        # File operations
        self.new_btn.clicked.connect(self._new_project)
        self.open_btn.clicked.connect(self._open_project)
        self.save_btn.clicked.connect(self._save_project)
        self.save_as_btn.clicked.connect(self._save_as_project)
        
        # Code operations
        self.generate_btn.clicked.connect(self._generate_lua_code)
        self.export_lua_btn.clicked.connect(self._export_lua_file)
        self.engine_btn.clicked.connect(self._open_engine_settings)
        
        # Block operations
        self.library_widget.block_selected.connect(self._add_block_from_library)
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        self.fit_view_btn.clicked.connect(self._fit_view)
        self.delete_btn.clicked.connect(self._delete_selected)
        
        # Scene signals
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
        self.project_tree.clear()
        self.code_preview.clear()
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
                
                # Clear current scene
                self.block_scene.clear()
                self.blocks.clear()
                self.connections.clear()
                
                # Load blocks
                for block_data in data.get('blocks', []):
                    from .block_components import LuaBlock
                    block = LuaBlock.from_dict(block_data)
                    self.block_scene.addItem(block)
                    self.blocks.append(block)
                
                # Load engine settings if present
                if 'engine_settings' in data:
                    self.engine_settings = data['engine_settings']
                    engine_name = self.engine_settings.get('engine', 'lua').upper()
                    self.engine_label.setText(f"Engine: {engine_name}")
                
                # Update UI
                self._update_project_tree()
                self.current_file = Path(file_path)
                self.file_info_label.setText(f"Loaded: {self.current_file.name}")
                self.status_label.setText(f"Project loaded: {self.current_file.name}")
                self.status_indicator.setStyleSheet("color: #2ecc71; font-size: 24px;")
                
                # Generate code preview
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
            # Collect block data
            blocks_data = []
            for item in self.block_scene.items():
                from .block_components import LuaBlock
                if isinstance(item, LuaBlock):
                    blocks_data.append(item.to_dict())
            
            # Create project data
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
            
            # Save to file
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
        
        # Get save location
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
        """Handle block addition"""
        self._update_project_tree()
    
    def _on_block_removed(self, block):
        """Handle block removal"""
        if block in self.blocks:
            self.blocks.remove(block)
        self._update_project_tree()
    
    def _update_project_tree(self):
        """Update project tree view"""
        self.project_tree.clear()
        
        for block in self.blocks:
            item = QListWidgetItem(f"▢ {block.title} (#{block.block_id})")
            item.block = block
            self.project_tree.addItem(item)
    
    def _zoom_in(self):
        """Zoom in the view"""
        self.block_view.scale(1.2, 1.2)
    
    def _zoom_out(self):
        """Zoom out the view"""
        self.block_view.scale(0.8, 0.8)
    
    def _fit_view(self):
        """Fit all blocks in view"""
        self.block_view.fitInView(self.block_scene.itemsBoundingRect(), Qt.KeepAspectRatio)
    
    def _delete_selected(self):
        """Delete selected blocks"""
        for item in self.block_scene.selectedItems():
            from .block_components import LuaBlock
            if isinstance(item, LuaBlock):
                item.block_deleted.emit(item)
    
    def _generate_lua_code(self, preview_only=False):
        """Generate Lua code from blocks"""
        try:
            # Find entry points (event blocks)
            entry_blocks = []
            for block in self.blocks:
                if hasattr(block, 'block_type') and block.block_type == 'event':
                    entry_blocks.append(block)
            
            if not entry_blocks and not preview_only:
                QMessageBox.warning(self, "No Entry Points", 
                                  "Add an 'On Start' or similar event block to generate code.")
                return
            
            # Generate code
            lua_code = self._generate_complete_code()
            
            # Update preview
            self.code_preview.update_code(lua_code)
            self.right_tabs.setCurrentIndex(0)  # Switch to code tab
            
            self.status_label.setText("Lua code generated")
            
            if not preview_only:
                # Auto-save generated code to temp file
                temp_dir = Path.home() / ".qha" / "temp_lua"
                temp_dir.mkdir(parents=True, exist_ok=True)
                temp_file = temp_dir / f"generated_{self._get_project_name()}.lua"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(lua_code)
                
                self.status_label.setText(f"Lua code generated and saved to temp file")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate Lua code: {str(e)}")
    
    def _generate_complete_code_old(self):
        """Generate complete Lua code with header and structure"""
        import datetime
        
        # Generate code from blocks
        lua_code = ""
        entry_blocks = [b for b in self.blocks if hasattr(b, 'block_type') and b.block_type == 'event']
        
        for entry_block in entry_blocks:
            if hasattr(entry_block, 'generate_lua_code'):
                block_code = entry_block.generate_lua_code()
                lua_code += block_code + "\n"
        
        # Create complete code with header
        project_name = self._get_project_name()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        engine = self.engine_settings['engine'].upper()
        
        header = f"""-- Generated by Drag-and-Drop Lua Blocks Plugin
-- Project: {project_name}
-- Engine: {engine}
-- Generated: {timestamp}
-- Memory Limit: {self.engine_settings['memory_limit']}MB
-- JIT: {'Enabled' if self.engine_settings['enable_jit'] else 'Disabled'}
-- Debug: {'Enabled' if self.engine_settings['debug_mode'] else 'Disabled'}

-- Initialization
print("=== {project_name} ===")
print("Engine: {engine}")
print("Generated: {timestamp}")

-- Main execution
local function main()
"""
        
        footer = """
end

-- Error handling wrapper
local success, err = pcall(main)
if not success then
    print("Error during execution:", err)
    if string.find(err, "not enough memory") then
        print("Tip: Try increasing memory limit in engine settings")
    end
else
    print("Execution completed successfully")
end

print("=== End of Program ===")
"""
        
        # Indent the generated code
        if lua_code.strip():
            indented_code = ""
            for line in lua_code.split('\n'):
                indented_code += "    " + line + "\n"
            return header + indented_code + footer
        else:
            return header + "    -- Add your Lua code here\n" + footer

    def _generate_complete_code(self):
        """Generate complete Lua code from ALL blocks with proper structure"""
        import datetime
        
        # Get project name
        project_name = self._get_project_name()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        engine = self.engine_settings['engine'].upper()
        
        # Collect ALL blocks by type
        all_blocks = []
        event_blocks = []
        variable_declarations = []
        function_definitions = []
        main_execution_blocks = []
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
        
        # Generate code sections
        code_sections = []
        
        # 1. Header
        header = f"""-- Generated by Drag-and-Drop Lua Blocks Plugin
-- Project: {project_name}
-- Engine: {engine}
-- Generated: {timestamp}
-- Memory Limit: {self.engine_settings['memory_limit']}MB
-- JIT: {'Enabled' if self.engine_settings['enable_jit'] else 'Disabled'}
-- Debug: {'Enabled' if self.engine_settings['debug_mode'] else 'Disabled'}
-- Blocks: {len(all_blocks)} total ({len(event_blocks)} events, {len(variable_declarations)} vars, {len(function_definitions)} funcs, {len(control_blocks)} controls, {len(math_blocks)} math, {len(quantum_blocks)} quantum)

print("=== {project_name} ===")
print("Engine: {engine}")
print("Generated: {timestamp}")
print("Total blocks: {len(all_blocks)}")
"""
        code_sections.append(header)
        
        # 2. Variable declarations (at the top, outside functions)
        if variable_declarations:
            code_sections.append("\n-- VARIABLE DECLARATIONS --")
            for block in variable_declarations:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code()
                    code_sections.append(block_code)
        
        # 3. Function definitions
        if function_definitions:
            code_sections.append("\n-- FUNCTION DEFINITIONS --")
            for block in function_definitions:
                if hasattr(block, 'generate_complete_code'):
                    block_code = block.generate_complete_code()
                    code_sections.append(block_code)
                elif hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code()
                    code_sections.append(block_code)
        
        # 4. Helper functions for quantum blocks (if any)
        if quantum_blocks:
            code_sections.append("""
-- QUANTUM HELPER FUNCTIONS --
-- These are simulated quantum operations for demonstration

local quantum_states = {}

function quantum_state(n_qubits)
    -- Create a simulated quantum state
    local state = {
        n_qubits = n_qubits,
        amplitudes = {},
        probabilities = {}
    }
    
    -- Initialize to |0⟩^n
    local total_states = 2^n_qubits
    for i = 0, total_states - 1 do
        state.amplitudes[i] = complex.new(i == 0 and 1 or 0, 0)
    end
    
    table.insert(quantum_states, state)
    print(string.format("Created quantum state with %d qubits", n_qubits))
    return #quantum_states
end

function apply_gate(state_id, gate_name, target_qubit)
    -- Apply a simulated quantum gate
    local state = quantum_states[state_id]
    if not state then
        error("Invalid quantum state ID")
    end
    
    print(string.format("Applying gate '%s' to qubit %d in state %d", 
          gate_name, target_qubit, state_id))
    return state_id
end

function measure(state_id)
    -- Simulate measurement
    local state = quantum_states[state_id]
    if not state then
        error("Invalid quantum state ID")
    end
    
    -- Simulate probabilistic measurement
    local result = math.random(0, 2^state.n_qubits - 1)
    print(string.format("Measured state %d: |%d⟩", state_id, result))
    return result
end

-- Complex number support for quantum simulations
local complex = {}
complex.__index = complex

function complex.new(real, imag)
    return setmetatable({real = real or 0, imag = imag or 0}, complex)
end

function complex:__tostring()
    return string.format("%.3f + %.3fi", self.real, self.imag)
end

function complex:conjugate()
    return complex.new(self.real, -self.imag)
end

function complex.__add(a, b)
    return complex.new(a.real + b.real, a.imag + b.imag)
end

function complex.__mul(a, b)
    return complex.new(
        a.real * b.real - a.imag * b.imag,
        a.real * b.imag + a.imag * b.real
    )
end
    """)
        
        # 5. Main execution logic
        code_sections.append("\n-- MAIN EXECUTION --")
        code_sections.append("local function main()")
        
        # Add indentation for main function body
        indent = "    "
        
        # 5a. Event blocks trigger execution
        if event_blocks:
            code_sections.append(f"\n{indent}-- EVENT HANDLERS --")
            for block in event_blocks:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code(1)  # Indent 1 level for main function
                    code_sections.append(block_code)
        
        # 5b. Control blocks (if, for, while)
        if control_blocks:
            code_sections.append(f"\n{indent}-- CONTROL STRUCTURES --")
            for block in control_blocks:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code(1)
                    code_sections.append(block_code)
        
        # 5c. Math operations
        if math_blocks:
            code_sections.append(f"\n{indent}-- MATH OPERATIONS --")
            for block in math_blocks:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code(1)
                    code_sections.append(block_code)
            
            # Add some example math if no specific math blocks
            if len(math_blocks) == 0:
                code_sections.append(f"{indent}-- Math operations will appear here --")
        
        # 5d. Quantum operations
        if quantum_blocks:
            code_sections.append(f"\n{indent}-- QUANTUM OPERATIONS --")
            for block in quantum_blocks:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code(1)
                    code_sections.append(block_code)
        
        # 5e. Action blocks (general operations)
        action_blocks = [b for b in self.blocks if hasattr(b, 'block_type') and b.block_type == 'action']
        if action_blocks:
            code_sections.append(f"\n{indent}-- ACTIONS --")
            for block in action_blocks:
                if hasattr(block, 'generate_lua_code'):
                    block_code = block.generate_lua_code(1)
                    code_sections.append(block_code)
        
        # Close main function
        code_sections.append("end\n")
        
        # 6. Error handling wrapper
        footer = """
-- ERROR HANDLING WRAPPER --
local success, err = pcall(main)
if not success then
    print("\\n=== ERROR ===")
    print("Error during execution:", err)
    
    -- Provide helpful hints based on error type
    if string.find(err, "attempt to perform arithmetic") then
        print("Hint: Check your math operations for type mismatches")
    elseif string.find(err, "attempt to call") then
        print("Hint: Make sure you're calling functions that exist")
    elseif string.find(err, "not enough memory") then
        print("Hint: Try increasing memory limit in engine settings")
    elseif string.find(err, "syntax error") then
        print("Hint: Check for missing parentheses, brackets, or quotes")
    end
    
    print("\\nStack trace:")
    debug.traceback(err, 2)
else
    print("\\n=== SUCCESS ===")
    print("Execution completed successfully")
    
    -- Show statistics if available
    if quantum_states and #quantum_states > 0 then
        print(string.format("Quantum states created: %d", #quantum_states))
    end
end

print("\\n=== End of Program ===")

-- Return success code for external calling
if success then
    return 0
else
    return 1
end
"""
        code_sections.append(footer)
        
        # Combine all sections
        complete_code = "\n".join(code_sections)
        return complete_code

    def _get_project_name(self):
        """Get project name from file or default"""
        if self.current_file:
            return self.current_file.stem
        return "UntitledProject"
    
    def _run_lua_code(self, engine_type=None):
        """Run the generated Lua code with selected engine"""
        code = self.code_preview.toPlainText()
        
        if not code.strip():
            QMessageBox.warning(self, "No Code", "Generate Lua code first.")
            return
        
        try:
            # Determine which engine to use
            if engine_type:
                engine_to_use = engine_type
            else:
                engine_to_use = self.engine_settings['engine']
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.status_label.setText(f"Executing with {engine_to_use.upper()}...")
            
            # Execute based on engine selection
            if engine_to_use == 'luajit':
                QTimer.singleShot(100, lambda: self._execute_with_luajit(code))
            else:
                QTimer.singleShot(100, lambda: self._execute_with_lua(code))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize Lua engine: {str(e)}")
            self.progress_bar.setVisible(False)
    
    def _execute_with_lua(self, code):
        """Execute code with standard Lua"""
        try:
            # Import Lua bridge
            from plugins.libs.lua_bridge import get_lua_bridge
            bridge = get_lua_bridge()
            
            # Create new state
            lua_state = bridge.init()
            if not lua_state:
                raise RuntimeError("Failed to initialize Lua state")
            
            # Set memory limit if available in settings - SIMPLIFIED
            if self.engine_settings['memory_limit'] > 0:
                # Use safe memory configuration that works with all Lua versions
                memory_code = f"""
local limit = {self.engine_settings['memory_limit']} * 1024 * 1024
print(string.format("Memory limit: %.1f MB", limit / (1024*1024)))
-- Safe memory configuration that works with all Lua versions
local function safe_gc_config()
    -- Try Lua 5.1 style
    local success, msg = pcall(function()
        collectgarbage("setpause", 100)
        collectgarbage("setstepmul", 200)
    end)
    if success then
        print("Using Lua 5.1 GC settings")
        return
    end
    
    -- Try Lua 5.2+ incremental
    success, msg = pcall(function()
        collectgarbage("incremental", 100, 200)
    end)
    if success then
        print("Using Lua 5.2+ incremental GC")
        return
    end
    
    -- Try Lua 5.4 generational
    success, msg = pcall(function()
        collectgarbage("generational", 100, 200)
    end)
    if success then
        print("Using Lua 5.4 generational GC")
        return
    end
    
    -- If nothing works, just continue
    print("Using default GC settings")
end
safe_gc_config()
"""
                try:
                    bridge.execute_script(lua_state, memory_code)
                    print("Memory limit configured")
                except:
                    print("Memory limit configuration skipped")
            
            # Execute main code
            success = bridge.execute_script(lua_state, code)
            
            if success:
                self.status_label.setText("Lua execution completed successfully")
                QMessageBox.information(self, "Success", "Lua code executed successfully!")
            else:
                error_msg = self._get_lua_error(bridge, lua_state)
                self.status_label.setText("Lua execution failed")
                QMessageBox.critical(self, "Lua Error", f"Execution failed:\n{error_msg}")
            
            # Cleanup
            bridge.cleanup(lua_state)
            
        except ImportError:
            # Demo mode
            self._run_in_demo_mode(code, "Lua")
        except Exception as e:
            error_msg = str(e)
            self.status_label.setText(f"Execution error: {error_msg}")
            QMessageBox.critical(self, "Error", f"Failed to execute Lua code:\n{error_msg}")
        finally:
            self.progress_bar.setVisible(False)
    
    def _execute_with_luajit(self, code):
        """Execute code with LuaJIT"""
        try:
            # Import LuaJIT bridge
            from plugins.libs.luajit_bridge import get_luajit_bridge
            bridge = get_luajit_bridge()
            
            # Create new state
            lua_state = bridge.init()
            if not lua_state:
                raise RuntimeError("Failed to initialize LuaJIT state")
            
            # Configure LuaJIT settings
            jit_config = ""
            if self.engine_settings['enable_jit']:
                jit_config = """
-- Enable JIT compiler
jit.on()
jit.flush()
print("LuaJIT JIT compiler: ON")
"""
            else:
                jit_config = """
-- Disable JIT compiler
jit.off()
print("LuaJIT JIT compiler: OFF")
"""
            
            # Execute JIT config
            bridge.execute_script(lua_state, jit_config)
            
            # Execute main code
            success = bridge.execute_script(lua_state, code)
            
            if success:
                self.status_label.setText("LuaJIT execution completed successfully")
                QMessageBox.information(self, "Success", "LuaJIT code executed successfully!")
            else:
                error_msg = "LuaJIT execution failed"
                self.status_label.setText("LuaJIT execution failed")
                QMessageBox.critical(self, "LuaJIT Error", f"Execution failed:\n{error_msg}")
            
            # Cleanup
            bridge.lib.lua_close(lua_state)
            
        except ImportError:
            # Fall back to standard Lua
            print("LuaJIT not available, falling back to Lua")
            self._execute_with_lua(code)
        except Exception as e:
            error_msg = str(e)
            self.status_label.setText(f"LuaJIT execution error: {error_msg}")
            QMessageBox.critical(self, "Error", f"Failed to execute with LuaJIT:\n{error_msg}")
            # Try with standard Lua as fallback
            self._execute_with_lua(code)
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
        
        # Info label
        info_label = QLabel(f"{engine_name} bridge not available. Running in demo mode.")
        info_label.setStyleSheet("color: #e67e22; font-weight: bold;")
        layout.addWidget(info_label)
        
        # Code display
        code_text = QTextEdit()
        code_text.setPlainText(code)
        code_text.setReadOnly(True)
        code_text.setFont(QFont("Consolas", 10))
        layout.addWidget(code_text)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(demo_dialog.accept)
        layout.addWidget(close_btn)
        
        demo_dialog.exec()
        
        self.status_label.setText("Code displayed in demo mode")
    
    def _show_run_options(self):
        """Show run options in a simple dialog"""
        from PySide6.QtWidgets import QMenu
        
        menu = QMenu(self)
        
        run_lua_action = menu.addAction("Run with Lua")
        run_lua_action.triggered.connect(lambda: self._run_lua_code('lua'))
        
        run_luajit_action = menu.addAction("Run with LuaJIT")
        run_luajit_action.triggered.connect(lambda: self._run_lua_code('luajit'))
        
        menu.addSeparator()
        
        run_debug_action = menu.addAction("Run with Debug Mode")
        run_debug_action.triggered.connect(lambda: self._run_lua_code('debug'))
        
        # Show menu at button position
        menu.exec(self.run_settings_btn.mapToGlobal(self.run_settings_btn.rect().bottomLeft()))