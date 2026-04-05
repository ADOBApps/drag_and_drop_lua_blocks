"""
enhanced_terminal.py - Enhanced Lua/LuaJIT terminal with multi-line support
"""

import json
import re
from pathlib import Path
from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QTextCursor, QPalette


class EnhancedLuaTerminal(QTextEdit):
    """
    Enhanced Lua/LuaJIT terminal with:
    - Multi-line input (Shift+Enter)
    - Command history with persistence
    - Syntax highlighting
    - Execution timing display
    - Return value capture
    """
    
    command_executed = Signal(str)
    
    def __init__(self, parent=None, engine_type="lua"):
        super().__init__(parent)
        self.engine_type = engine_type
        self.history = []
        self.history_index = -1
        self.prompt = ">>> "
        self.continuation_prompt = "... "
        self.in_multiline = False
        self.multiline_buffer = []
        
        self._setup_ui()
        self._load_history()
    
    def _setup_ui(self):
        """Setup terminal appearance"""
        font = QFont("Courier New", 10)
        font.setFixedPitch(True)
        self.setFont(font)
        
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor(30, 30, 46))
        palette.setColor(QPalette.Text, QColor(248, 248, 242))
        self.setPalette(palette)
        
        self._write_welcome()
    
    def _write_welcome(self):
        """Write welcome message"""
        self.append("=" * 70)
        self.append(f"Enhanced {self.engine_type.upper()} Interactive Terminal")
        self.append("=" * 70)
        self.append("")
        self.append("Commands:")
        self.append("  • Type Lua code and press Enter to execute")
        self.append("  • Shift+Enter for multi-line input")
        self.append("  • Up/Down arrows to navigate history")
        self.append("  • Ctrl+L to clear terminal")
        self.append("")
        self.append("Example:")
        self.append('  >>> x = 42')
        self.append('  >>> print(x)')
        self.append('  42')
        self.append('  >>> function add(a,b) return a+b end')
        self.append('  >>> add(10, 32)')
        self.append('  -> 42')
        self.append("=" * 70)
        self.append("")
        self._write_prompt()
    
    def _write_prompt(self):
        """Write prompt"""
        prompt = self.continuation_prompt if self.in_multiline else self.prompt
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(prompt)
        self.setTextCursor(cursor)
    
    def _get_current_line(self) -> str:
        """Get current input line"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        line = cursor.selectedText()
        if line.startswith(self.prompt) or line.startswith(self.continuation_prompt):
            prompt_len = len(self.prompt) if line.startswith(self.prompt) else len(self.continuation_prompt)
            line = line[prompt_len:]
        return line
    
    def _needs_more_lines(self, command: str) -> bool:
        """Check if command needs more lines"""
        command = command.strip()
        return (command.startswith('function') and not command.endswith('end')) or \
               (command.startswith('if') and 'then' in command and not command.endswith('end')) or \
               (command.startswith('for') and 'do' in command and not command.endswith('end')) or \
               (command.startswith('while') and 'do' in command and not command.endswith('end')) or \
               (command.startswith('repeat') and not command.startswith('until'))
    
    def _is_complete_block(self, code: str) -> bool:
        """Check if multi-line block is complete"""
        lines = code.split('\n')
        open_blocks = 0
        close_blocks = 0
        
        for line in lines:
            line = line.strip()
            if line.startswith('function') or line.startswith('if') or line.startswith('for') or line.startswith('while'):
                open_blocks += 1
            if line == 'end' or line.startswith('end'):
                close_blocks += 1
            if line.startswith('until'):
                close_blocks += 1
        
        return open_blocks <= close_blocks
    
    def _execute_line(self):
        """Execute current input"""
        if self.in_multiline:
            current_line = self._get_current_line()
            self.multiline_buffer.append(current_line)
            
            full_input = '\n'.join(self.multiline_buffer)
            if self._is_complete_block(full_input):
                self._execute_command(full_input)
                self.multiline_buffer = []
                self.in_multiline = False
            else:
                self.textCursor().insertText("\n")
                self._write_prompt()
        else:
            command = self._get_current_line()
            if command:
                if self._needs_more_lines(command):
                    self.multiline_buffer = [command]
                    self.in_multiline = True
                    self.textCursor().insertText("\n")
                    self._write_prompt()
                else:
                    self._execute_command(command)
                    self._write_prompt()
            else:
                self.textCursor().insertText("\n")
                self._write_prompt()
    
    def _execute_command(self, command: str):
        """Execute command"""
        self.history.append(command)
        self.history_index = len(self.history)
        self._save_history()
        
        self.textCursor().insertText(command + "\n")
        self.command_executed.emit(command)
        self.ensureCursorVisible()
    
    def append_output(self, text: str):
        """Append output"""
        self.textCursor().insertText(text + "\n")
        self.ensureCursorVisible()
    
    def append_return_value(self, value):
        """Append return value"""
        self.textCursor().insertHtml(f'<span style="color: #50fa7b;">→ {value}</span>\n')
        self.ensureCursorVisible()
    
    def append_error(self, error: str, line_number: int = None):
        """Append error"""
        if line_number:
            self.textCursor().insertHtml(f'<span style="color: #ff5555;">Line {line_number}: {error}</span>\n')
        else:
            self.textCursor().insertHtml(f'<span style="color: #ff5555;">{error}</span>\n')
        self.ensureCursorVisible()
    
    def append_success(self, text: str):
        """Append success"""
        self.textCursor().insertHtml(f'<span style="color: #50fa7b;">✓ {text}</span>\n')
        self.ensureCursorVisible()
    
    def append_warning(self, text: str):
        """Append warning"""
        self.textCursor().insertHtml(f'<span style="color: #f1fa8c;">⚠ {text}</span>\n')
        self.ensureCursorVisible()
    
    def append_timing(self, seconds: float):
        """Append timing"""
        color = "#50fa7b" if seconds < 0.1 else "#f1fa8c" if seconds < 1 else "#ff5555"
        self.textCursor().insertHtml(f'<span style="color: {color};">⏱ {seconds*1000:.2f}ms</span>\n')
        self.ensureCursorVisible()
    
    def clear(self):
        """Clear terminal"""
        super().clear()
        self._write_welcome()
    
    def _save_history(self):
        """Save history"""
        try:
            history_file = Path.home() / ".qha" / "terminal_history.json"
            history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(history_file, 'w') as f:
                json.dump(self.history[-500:], f)
        except:
            pass
    
    def _load_history(self):
        """Load history"""
        try:
            history_file = Path.home() / ".qha" / "terminal_history.json"
            if history_file.exists():
                with open(history_file, 'r') as f:
                    self.history = json.load(f)
                    self.history_index = len(self.history)
        except:
            pass
    
    def keyPressEvent(self, event):
        """Handle keyboard"""
        # Ctrl+L - Clear
        if event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
            self.clear()
            event.accept()
            return
        
        # Shift+Enter - New line
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                self.textCursor().insertText("\n")
                if self.in_multiline:
                    pass
                event.accept()
                return
            else:
                self._execute_line()
                event.accept()
                return
        
        # Up/Down - History
        if event.key() == Qt.Key_Up:
            if self.history and self.history_index > 0:
                self.history_index -= 1
                self._clear_current_line()
                self.textCursor().insertText(self.history[self.history_index])
            event.accept()
            return
        
        if event.key() == Qt.Key_Down:
            if self.history and self.history_index < len(self.history) - 1:
                self.history_index += 1
                self._clear_current_line()
                self.textCursor().insertText(self.history[self.history_index])
            elif self.history_index == len(self.history) - 1:
                self.history_index = len(self.history)
                self._clear_current_line()
            event.accept()
            return
        
        # Home - Jump to prompt
        if event.key() == Qt.Key_Home:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.End)
            line_start = cursor.block().position()
            prompt_len = len(self.prompt) if not self.in_multiline else len(self.continuation_prompt)
            cursor.setPosition(line_start + prompt_len)
            self.setTextCursor(cursor)
            event.accept()
            return
        
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        super().keyPressEvent(event)
    
    def _clear_current_line(self):
        """Clear current input line"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        self._write_prompt()