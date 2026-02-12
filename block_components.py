"""
Block Components - Core classes for block programming
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

import json
import uuid
import math
from typing import Dict, List, Any, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QGraphicsView,
    QGraphicsScene, QGraphicsItem, QGraphicsTextItem,
    QGraphicsLineItem, QGraphicsDropShadowEffect, QToolBox,
    QGroupBox, QComboBox, QInputDialog, QMessageBox, QMenu,
    QGraphicsObject, QStyleOptionGraphicsItem
)
from PySide6.QtGui import (
    QFont, QColor, QBrush, QPen, QLinearGradient, QPainter,
    QDrag, QPixmap, QIcon, QCursor, QAction, QTextCursor,
    QTextCharFormat, QPainterPath, QPolygonF
)
from PySide6.QtCore import (
    Qt, Signal, Slot, QPoint, QPointF, QRectF, QSize,
    QMimeData, QByteArray, QDataStream, QIODevice,
    QObject
)
import re


class Connection(QGraphicsLineItem):
    """Connection line between sockets"""
    
    def __init__(self, start_socket, end_socket, parent=None):
        super().__init__(parent)
        self.start_socket = start_socket
        self.end_socket = end_socket
        
        # Visual properties
        self.setPen(QPen(QColor(100, 100, 100), 2))
        self.setZValue(-1)  # Behind blocks
        
        # Update connection line
        self.update_line()
    
    def update_line(self):
        """Update the connection line between sockets"""
        if self.start_socket and self.end_socket:
            # Get socket positions in scene coordinates
            start_pos = self.start_socket.scenePos()
            end_pos = self.end_socket.scenePos()
            
            # Adjust positions to center of sockets
            start_pos += QPointF(self.start_socket.SOCKET_SIZE / 2, 
                               self.start_socket.SOCKET_SIZE / 2)
            end_pos += QPointF(self.end_socket.SOCKET_SIZE / 2, 
                             self.end_socket.SOCKET_SIZE / 2)
            
            # Set line
            self.setLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y())
    
    def paint(self, painter, option, widget=None):
        """Paint the connection with arrow head"""
        super().paint(painter, option, widget)
        
        # Draw arrow head at the end
        line = self.line()
        if line.length() > 0:
            # Calculate arrow position
            end_point = line.p2()
            
            # Calculate angle
            dx = line.x2() - line.x1()
            dy = line.y2() - line.y1()
            angle = math.atan2(dy, dx) * 180 / math.pi
            
            # Create arrow polygon
            arrow_size = 10
            arrow = QPolygonF()
            arrow.append(QPointF(0, 0))
            arrow.append(QPointF(-arrow_size, arrow_size / 2))
            arrow.append(QPointF(-arrow_size, -arrow_size / 2))
            
            # Transform to correct position and rotation
            painter.save()
            painter.translate(end_point)
            painter.rotate(angle)
            painter.setBrush(QBrush(QColor(100, 100, 100)))
            painter.setPen(QPen(Qt.NoPen))
            painter.drawPolygon(arrow)
            painter.restore()


class Socket(QGraphicsObject):
    """Socket for connecting blocks"""
    
    SOCKET_SIZE = 12
    socket_clicked = Signal(object)  # Signal emitted when socket is clicked
    
    def __init__(self, block, name: str, socket_type: str, direction: str, 
                 data_type: str):
        super().__init__(block)
        self.block = block
        self.name = name
        self.socket_type = socket_type
        self.direction = direction  # "input" or "output"
        self.data_type = data_type
        
        # Connection tracking
        self.connections = []  # List of Connection objects
        self.connected_to = None  # Other socket this is connected to
        
        # Visual properties
        self._rect = QRectF(0, 0, self.SOCKET_SIZE, self.SOCKET_SIZE)
        self.setAcceptHoverEvents(True)
        
        # Label
        self.label = QGraphicsTextItem(name, self)
        self.label.setDefaultTextColor(Qt.white)
        small_font = QFont("Arial", 7)
        self.label.setFont(small_font)
        
        # Position label based on direction
        if self.direction == "input":
            self.label.setPos(self.SOCKET_SIZE + 3, -5)
        else:
            self.label.setPos(-self.label.boundingRect().width() - 3, -5)
    
    def boundingRect(self):
        """Required override for QGraphicsItem"""
        return self._rect
    
    def paint(self, painter, option, widget=None):
        """Paint the socket"""
        color = self._get_socket_color()
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawEllipse(self._rect)
        
        # Highlight if hovered
        if self.isUnderMouse():
            painter.setPen(QPen(Qt.yellow, 2))
            painter.drawEllipse(self._rect)
    
    def mousePressEvent(self, event):
        """Handle mouse press on socket"""
        self.socket_clicked.emit(self)
        event.accept()
    
    def _get_socket_color(self) -> QColor:
        """Get color based on data type"""
        colors = {
            'any': QColor(200, 200, 200),
            'number': QColor(66, 165, 245),
            'string': QColor(76, 175, 80),
            'boolean': QColor(255, 152, 0),
            'table': QColor(156, 39, 176),
            'function': QColor(244, 67, 54),
        }
        return colors.get(self.data_type, QColor(200, 200, 200))
    
    def can_connect_to(self, other_socket) -> bool:
        """Check if this socket can connect to another socket"""
        # Can't connect to self
        if self == other_socket:
            return False
        
        # Can't connect to socket in same block
        if self.block == other_socket.block:
            return False
        
        # Check direction compatibility
        if self.direction == other_socket.direction:
            return False
        
        # Check type compatibility
        if self.data_type != "any" and other_socket.data_type != "any":
            if self.data_type != other_socket.data_type:
                return False
        
        return True
    
    def connect_to(self, other_socket) -> bool:
        """Connect this socket to another socket"""
        if self.can_connect_to(other_socket):
            # Create connection
            connection = Connection(self, other_socket)
            
            # Add to scene
            if self.scene():
                self.scene().addItem(connection)
            
            # Track connection
            self.connections.append(connection)
            other_socket.connections.append(connection)
            
            self.connected_to = other_socket
            other_socket.connected_to = self
            
            return True
        return False
    
    def disconnect(self):
        """Disconnect this socket from all connections"""
        for connection in self.connections[:]:
            # Remove from other socket
            if connection.start_socket == self and connection.end_socket.connected_to == self:
                connection.end_socket.connected_to = None
            elif connection.end_socket == self and connection.start_socket.connected_to == self:
                connection.start_socket.connected_to = None
            
            # Remove connection from scene
            if connection.scene():
                connection.scene().removeItem(connection)
        
        self.connections.clear()
        self.connected_to = None


class LuaBlock(QGraphicsObject):
    """Base class for Lua programming blocks"""
    
    # Signals must be defined at class level
    block_moved = Signal(object, QPointF)
    block_selected = Signal(object)
    block_deleted = Signal(object)
    block_duplicated = Signal(object, object)  # original, duplicate
    
    TYPE_COLORS = {
        'event': QColor(0, 150, 136),      # Teal
        'action': QColor(156, 39, 176),    # Purple
        'control': QColor(255, 87, 34),    # Deep Orange
        'variable': QColor(3, 169, 244),   # Light Blue
        'function': QColor(76, 175, 80),   # Green
        'operator': QColor(255, 193, 7),   # Amber
        'value': QColor(121, 85, 72),      # Brown
    }
    
    def __init__(self, block_type: str, title: str, parent=None):
        super().__init__(parent)
        self.block_type = block_type
        self.block_id = str(uuid.uuid4())[:8]
        self.title = title
        self.description = ""
        self.sockets = {}  # name -> Socket object
        self.lua_code = ""
        self.data = {}
        
        # Setup visuals
        self._setup_appearance()
        self._setup_ui()
        
        # Enable flags
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
    
    def _setup_appearance(self):
        """Setup block appearance"""
        # Colors
        base_color = self.TYPE_COLORS.get(self.block_type, QColor(100, 100, 100))
        self.base_color = base_color
        self.highlight_color = base_color.lighter(130)
        self.shadow_color = base_color.darker(150)
        
        # Size based on block type
        if self.block_type == 'event':
            self.width = 200
            self.height = 60
        elif self.block_type == 'control':
            self.width = 220
            self.height = 80
        else:
            self.width = 180
            self.height = 70
        
        # Bounding rectangle
        self._rect = QRectF(0, 0, self.width, self.height)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)
    
    def boundingRect(self):
        """Required override for QGraphicsItem"""
        return self._rect
    
    def paint(self, painter, option, widget=None):
        """Custom paint method for the block"""
        # Background with gradient
        gradient = QLinearGradient(0, 0, 0, self.height)
        gradient.setColorAt(0, self.base_color)
        gradient.setColorAt(1, self.base_color.darker(120))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(self.shadow_color, 1.5))
        painter.drawRoundedRect(self._rect, 4, 4)
        
        # Highlight if selected
        if self.isSelected():
            painter.setPen(QPen(Qt.yellow, 2))
            painter.drawRoundedRect(self._rect, 4, 4)
    
    def _setup_ui(self):
        """Setup block UI elements"""
        # Title area
        self.title_item = QGraphicsTextItem(self.title, self)
        self.title_item.setDefaultTextColor(Qt.white)
        font = QFont("Arial", 9, QFont.Bold)
        self.title_item.setFont(font)
        self.title_item.setPos(10, 10)
        
        # ID label (small)
        self.id_item = QGraphicsTextItem(f"#{self.block_id}", self)
        self.id_item.setDefaultTextColor(Qt.white)
        small_font = QFont("Arial", 6)
        self.id_item.setFont(small_font)
        self.id_item.setPos(self.width - 35, 5)
        
        # Add default sockets based on block type
        self._add_default_sockets()
    
    def _add_default_sockets(self):
        """Add default sockets based on block type"""
        if self.block_type == 'event':
            # Events have output sockets
            self.add_socket("trigger", "execution", "output", "any")
        elif self.block_type == 'action':
            # Actions have input and output
            self.add_socket("exec_in", "execution", "input", "any")
            self.add_socket("exec_out", "execution", "output", "any")
        elif self.block_type == 'control':
            if "If" in self.title:
                self.add_socket("condition", "value", "input", "boolean")
                self.add_socket("then_out", "execution", "output", "any")
                self.add_socket("else_out", "execution", "output", "any")
            elif "Loop" in self.title:
                self.add_socket("condition", "value", "input", "boolean")
                self.add_socket("loop_out", "execution", "output", "any")
        elif self.block_type == 'function':
            self.add_socket("result", "value", "output", "any")
    
    def add_socket(self, name: str, socket_type: str, direction: str, data_type: str) -> Socket:
        """Add a socket to the block"""
        socket = Socket(self, name, socket_type, direction, data_type)
        self.sockets[name] = socket
        
        # Position socket based on direction
        self._position_sockets()
        
        # Connect socket signals
        socket.socket_clicked.connect(self._on_socket_clicked)
        
        return socket
    
    def _position_sockets(self):
        """Position all sockets on the block"""
        input_sockets = [s for s in self.sockets.values() if s.direction == "input"]
        output_sockets = [s for s in self.sockets.values() if s.direction == "output"]
        
        # Position input sockets on left side
        input_y = 30
        input_spacing = 25
        for socket in input_sockets:
            socket.setPos(0, input_y)
            socket.label.setPos(socket.SOCKET_SIZE + 3, input_y - 5)
            input_y += input_spacing
        
        # Position output sockets on right side
        output_y = 30
        output_spacing = 25
        for socket in output_sockets:
            socket.setPos(self.width - socket.SOCKET_SIZE, output_y)
            socket.label.setPos(-socket.label.boundingRect().width() - 3, output_y - 5)
            output_y += output_spacing
    
    def _on_socket_clicked(self, socket):
        """Handle socket click - will be connected to scene's connection logic"""
        # This signal will be connected to the scene's connection handler
        pass
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        super().mousePressEvent(event)
        self.block_selected.emit(self)
        event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move (dragging)"""
        super().mouseMoveEvent(event)
        self.block_moved.emit(self, self.pos())
        event.accept()
        
        # Update all connections when block moves
        for socket in self.sockets.values():
            for connection in socket.connections:
                connection.update_line()
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click to edit"""
        self._open_edit_dialog()
        event.accept()
    
    def contextMenuEvent(self, event):
        """Show context menu"""
        menu = QMenu()
        
        edit_action = menu.addAction("Edit Block")
        delete_action = menu.addAction("Delete Block")
        menu.addSeparator()
        duplicate_action = menu.addAction("Duplicate Block")
        
        action = menu.exec(event.screenPos())
        
        if action == edit_action:
            self._open_edit_dialog()
        elif action == delete_action:
            self.block_deleted.emit(self)
        elif action == duplicate_action:
            self._duplicate_block()
    
    def _open_edit_dialog(self):
        """Open block edit dialog"""
        title, ok = QInputDialog.getText(
            None, "Edit Block", "Enter new title:", 
            text=self.title
        )
        
        if ok and title.strip():
            self.title = title.strip()
            self.title_item.setPlainText(self.title)
    
    def _duplicate_block(self):
        """Duplicate this block with connections"""
        # Get the parent scene
        scene = self.scene()
        if not scene:
            return
        
        try:
            # Create duplicate block
            duplicate = LuaBlock(self.block_type, f"{self.title} (Copy)")
            
            # Copy properties
            duplicate.lua_code = self.lua_code
            duplicate.description = self.description
            duplicate.data = self.data.copy() if self.data else {}
            
            # Position offset
            duplicate.setPos(self.x() + 30, self.y() + 30)
            
            # Copy sockets
            for name, socket in self.sockets.items():
                duplicate.add_socket(
                    name, 
                    socket.socket_type, 
                    socket.direction, 
                    socket.data_type
                )
            
            # Add to scene
            scene.addItem(duplicate)
            
            # Connect signals
            duplicate.block_deleted.connect(scene._on_block_deleted)
            
            # Emit signal if the scene supports it
            if hasattr(scene, 'block_added'):
                scene.block_added.emit(duplicate)
            
            # Emit duplication signal
            self.block_duplicated.emit(self, duplicate)
            
            # Note: Connections are NOT duplicated to avoid complexity
            # Users can reconnect the duplicate block as needed
            
        except Exception as e:
            print(f"Error duplicating block: {e}")
            QMessageBox.warning(None, "Duplication Error", f"Failed to duplicate block: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary"""
        return {
            'type': self.block_type,
            'id': self.block_id,
            'title': self.title,
            'description': self.description,
            'position': {'x': self.x(), 'y': self.y()},
            'sockets': {name: {
                'type': socket.socket_type,
                'direction': socket.direction,
                'data_type': socket.data_type
            } for name, socket in self.sockets.items()},
            'lua_code': self.lua_code,
            'data': self.data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create block from dictionary"""
        block = cls(data['type'], data['title'])
        block.block_id = data.get('id', block.block_id)
        block.description = data.get('description', '')
        block.lua_code = data.get('lua_code', '')
        block.data = data.get('data', {})
        
        # Set position
        if 'position' in data:
            block.setPos(data['position']['x'], data['position']['y'])
        
        # Add sockets
        if 'sockets' in data:
            for name, socket_data in data['sockets'].items():
                block.add_socket(
                    name,
                    socket_data['type'],
                    socket_data['direction'],
                    socket_data['data_type']
                )
        
        return block
    
    def generate_lua_code(self, indent: int = 0) -> str:
        """Generate Lua code from this block"""
        indent_str = '    ' * indent
        
        if self.lua_code:
            # Replace placeholders with connected values
            code = self.lua_code
            
            # For sockets with connections, replace placeholders
            for socket_name, socket in self.sockets.items():
                if socket.connected_to and socket.direction == "input":
                    # Get code from connected block
                    connected_code = socket.connected_to.block.generate_lua_code(indent)
                    placeholder = f"{{{socket_name}}}"
                    if placeholder in code:
                        code = code.replace(placeholder, connected_code.strip())
            
            return f"{indent_str}{code}\n"
        
        return f"{indent_str}-- {self.title} block\n"
    
    def get_connected_code(self, socket_name: str) -> str:
        """Get code from connected block via specified socket"""
        socket = self.sockets.get(socket_name)
        if socket and socket.connected_to:
            return socket.connected_to.block.generate_lua_code()
        return ""
    
    # In the LuaBlock class, enhance the generate_lua_code method:

    def generate_lua_code(self, indent: int = 0) -> str:
        """Generate Lua code from this block with proper indentation and logic"""
        indent_str = '    ' * indent
        
        # Default code templates based on block type
        if not self.lua_code and self.block_type != 'event':
            # Generate default code based on block type
            self.lua_code = self._get_default_code_template()
        
        if self.lua_code:
            code = self.lua_code
            
            # Process placeholders for all socket types
            placeholders_processed = set()
            
            # Process input sockets first (they provide values)
            for socket_name, socket in self.sockets.items():
                if socket.direction == "input":
                    placeholder = f"{{{socket_name}}}"
                    if placeholder in code and placeholder not in placeholders_processed:
                        if socket.connected_to:
                            # Get code from connected block
                            connected_block = socket.connected_to.block
                            connected_code = connected_block.generate_lua_code(indent)
                            # Clean up the connected code
                            connected_code_clean = connected_code.strip()
                            code = code.replace(placeholder, connected_code_clean)
                        else:
                            # Use default value
                            default_value = self._get_default_value(socket.data_type)
                            code = code.replace(placeholder, default_value)
                        placeholders_processed.add(placeholder)
            
            # Process output sockets (they receive values)
            for socket_name, socket in self.sockets.items():
                if socket.direction == "output" and socket.connected_to:
                    # This block's output is used elsewhere, ensure we generate proper code
                    pass
            
            # Format with proper indentation
            lines = code.split('\n')
            formatted_lines = []
            current_indent = indent
            
            for line in lines:
                line = line.rstrip()
                if not line:
                    formatted_lines.append('')
                    continue
                
                # Adjust indentation for control structures
                if line.strip().startswith('end') or line.strip().startswith('else') or line.strip().startswith('elseif'):
                    current_indent = max(0, current_indent - 1)
                
                formatted_line = ('    ' * current_indent) + line
                formatted_lines.append(formatted_line)
                
                # Increase indentation after certain keywords
                if (line.strip().endswith('then') or 
                    line.strip().endswith('do') or 
                    line.strip().startswith('function')):
                    current_indent += 1
            
            return '\n'.join(formatted_lines)
        
        # Fallback for blocks without specific code
        comment = f"-- {self.title} block"
        if hasattr(self, 'description') and self.description:
            comment += f": {self.description}"
        return f"{indent_str}{comment}\n"

    def _get_default_code_template(self) -> str:
        """Get default code template based on block type and title"""
        title_lower = self.title.lower()
        
        if self.block_type == 'control':
            if 'if' in title_lower or 'then' in title_lower:
                return "if {condition} then\n    -- then block\nend"
            elif 'for' in title_lower and 'loop' in title_lower:
                return "for {variable} = {start}, {end} do\n    -- loop body\nend"
            elif 'while' in title_lower:
                return "while {condition} do\n    -- loop body\nend"
            elif 'repeat' in title_lower:
                return "repeat\n    -- loop body\nuntil {condition}"
        
        elif self.block_type == 'operator':
            if 'add' in title_lower or '+' in self.title:
                return "{a} + {b}"
            elif 'subtract' in title_lower or '-' in self.title:
                return "{a} - {b}"
            elif 'multiply' in title_lower or '×' in self.title or '*' in self.title:
                return "{a} * {b}"
            elif 'divide' in title_lower or '÷' in self.title or '/' in self.title:
                return "{a} / {b}"
            elif 'equal' in title_lower:
                return "{a} == {b}"
            elif 'not equal' in title_lower:
                return "{a} ~= {b}"
            elif 'greater' in title_lower:
                return "{a} > {b}"
            elif 'less' in title_lower:
                return "{a} < {b}"
        
        elif self.block_type == 'variable':
            if 'set' in title_lower:
                return "{var_name} = {value}"
            elif 'get' in title_lower:
                return "{var_name}"
            elif 'increment' in title_lower:
                return "{var_name} = {var_name} + 1"
            elif 'decrement' in title_lower:
                return "{var_name} = {var_name} - 1"
        
        elif self.block_type == 'function':
            if 'quantum' in title_lower:
                return "quantum_state({n_qubits})"
            elif 'gate' in title_lower:
                return "apply_gate({state}, {gate}, {qubit})"
            elif 'measure' in title_lower:
                return "measure({state})"
            elif 'print' in title_lower:
                return 'print("{message}")'
            elif 'input' in title_lower:
                return 'io.read()'
        
        # Default template for unknown blocks
        return f"-- TODO: Implement {self.title} functionality"
    
    def _get_default_value(self, data_type: str) -> str:
        """Get default value for data type"""
        defaults = {
            'number': '0',
            'string': '""',
            'boolean': 'false',
            'table': '{}',
            'function': 'function() end',
            'any': 'nil'
        }
        return defaults.get(data_type, 'nil')
    
    def generate_complete_code(self) -> str:
        """Generate complete code block with this as entry point"""
        code = f"-- Block: {self.title} (ID: {self.block_id})\n"
        
        # Check what type of code this block needs
        if self.block_type == 'event':
            code += self.generate_lua_code(0)
        elif self.block_type == 'function':
            # Generate function definition
            func_name = self.data.get('function_name', f"block_{self.block_id}")
            params = self.data.get('parameters', '')
            code += f"function {func_name}({params})\n"
            code += self.generate_lua_code(1)
            code += "end\n\n"
            # If it's a main function, add call
            if self.data.get('is_main', False):
                code += f"{func_name}()\n"
        else:
            code += self.generate_lua_code(0)
        
        return code


class BlockScene(QGraphicsScene):
    """Graphics scene for block programming"""
    
    # Scene signals
    block_added = Signal(object)
    block_removed = Signal(object)
    connection_created = Signal(object, object)  # from_socket, to_socket
    connection_removed = Signal(object, object)  # from_socket, to_socket
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-1000, -1000, 2000, 2000)
        
        # Connection state
        self.connecting_socket = None
        self.temp_connection = None
        
    def add_block(self, block_data: Dict[str, Any]) -> Optional[LuaBlock]:
        """Add a block to the scene"""
        try:
            block = LuaBlock(block_data['type'], block_data['title'])
            
            # Set Lua code if provided
            if 'lua_code' in block_data:
                block.lua_code = block_data['lua_code']
            
            # Position block
            if 'position' in block_data:
                block.setPos(block_data['position']['x'], block_data['position']['y'])
            else:
                block.setPos(100, 100)
            
            # Add to scene
            self.addItem(block)
            
            # Connect signals
            block.block_deleted.connect(self._on_block_deleted)
            block.block_moved.connect(self._on_block_moved)
            
            # Connect socket signals
            for socket in block.sockets.values():
                socket.socket_clicked.connect(self._on_socket_clicked)
            
            self.block_added.emit(block)
            return block
            
        except Exception as e:
            print(f"Error adding block: {e}")
            return None
    
    def _on_block_deleted(self, block):
        """Handle block deletion"""
        # Remove all connections first
        for socket in block.sockets.values():
            socket.disconnect()
        
        # Remove block from scene
        self.removeItem(block)
        self.block_removed.emit(block)
    
    def _on_block_moved(self, block, pos):
        """Handle block movement - update connections"""
        for socket in block.sockets.values():
            for connection in socket.connections:
                connection.update_line()
    
    def _on_socket_clicked(self, socket):
        """Handle socket click for connection creation"""
        if not self.connecting_socket:
            # Start new connection
            self.connecting_socket = socket
            print(f"Started connection from {socket.name}")
        else:
            # Complete connection
            if self.connecting_socket.can_connect_to(socket):
                # Create permanent connection
                success = self.connecting_socket.connect_to(socket)
                if success:
                    self.connection_created.emit(self.connecting_socket, socket)
                    print(f"Connected {self.connecting_socket.name} to {socket.name}")
            
            # Clear connecting state
            self.connecting_socket = None
            
            # Remove temporary connection if it exists
            if self.temp_connection:
                self.removeItem(self.temp_connection)
                self.temp_connection = None
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for connection preview"""
        if self.connecting_socket:
            # Create or update temporary connection line
            if not self.temp_connection:
                self.temp_connection = Connection(self.connecting_socket, None)
                self.addItem(self.temp_connection)
            
            # Update end position
            scene_pos = event.scenePos()
            end_point = QPointF(scene_pos.x(), scene_pos.y())
            
            # Create a line from socket to mouse position
            start_pos = self.connecting_socket.scenePos()
            start_pos += QPointF(self.connecting_socket.SOCKET_SIZE / 2, 
                               self.connecting_socket.SOCKET_SIZE / 2)
            
            self.temp_connection.setLine(
                start_pos.x(), start_pos.y(),
                end_point.x(), end_point.y()
            )
        
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press to cancel connection"""
        if event.button() == Qt.RightButton and self.connecting_socket:
            # Cancel connection
            self.connecting_socket = None
            if self.temp_connection:
                self.removeItem(self.temp_connection)
                self.temp_connection = None
            event.accept()
        else:
            super().mousePressEvent(event)


class BlockProgrammingView(QGraphicsView):
    """Custom view for block programming"""
    
    def __init__(self, scene: BlockScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setInteractive(True)
        self.setBackgroundBrush(QBrush(QColor(240, 240, 240)))
        
        # View settings
        self.current_zoom = 1.0
    
    def wheelEvent(self, event):
        """Handle zoom with mouse wheel"""
        if event.modifiers() & Qt.ControlModifier:
            # Zoom in/out
            zoom_in = event.angleDelta().y() > 0
            factor = 1.2 if zoom_in else 0.8
            
            if (zoom_in and self.current_zoom < 3.0) or (not zoom_in and self.current_zoom > 0.2):
                self.scale(factor, factor)
                self.current_zoom *= factor
                event.accept()
        else:
            super().wheelEvent(event)


class BlockLibraryWidget(QToolBox):
    """Widget containing available Lua blocks"""
    
    block_selected = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.blocks = self._load_block_templates()
        self._setup_ui()
    
    def _load_block_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load block templates with complete code for all categories"""
        blocks = {
            'Events': [
                {'type': 'event', 'title': 'On Start', 'icon': '🚀',
                'description': 'Executes when program starts', 
                'lua_code': 'print("Program started")'},
                {'type': 'event', 'title': 'On Timer', 'icon': '⏱️',
                'description': 'Executes on timer interval',
                'lua_code': 'print("Timer event triggered")'},
                {'type': 'event', 'title': 'On Click', 'icon': '🖱️',
                'description': 'Executes on mouse click',
                'lua_code': 'print("Mouse clicked!")'},
            ],
            'Control': [
                {'type': 'control', 'title': 'If-Then', 'icon': '🔀',
                'description': 'Conditional execution',
                'lua_code': 'if {condition} then\n    -- then block\nend'},
                {'type': 'control', 'title': 'If-Else', 'icon': '⚖️',
                'description': 'Conditional with else branch',
                'lua_code': 'if {condition} then\n    -- then block\nelse\n    -- else block\nend'},
                {'type': 'control', 'title': 'For Loop', 'icon': '🔄',
                'description': 'For loop with counter',
                'lua_code': 'for {variable} = {start}, {end} do\n    -- loop body\nend'},
                {'type': 'control', 'title': 'While Loop', 'icon': '∞',
                'description': 'While condition is true',
                'lua_code': 'while {condition} do\n    -- loop body\nend'},
                {'type': 'control', 'title': 'Repeat-Until', 'icon': '↩️',
                'description': 'Repeat until condition',
                'lua_code': 'repeat\n    -- loop body\nuntil {condition}'},
            ],
            'Variables': [
                {'type': 'variable', 'title': 'Set Variable', 'icon': '📝',
                'description': 'Set variable value',
                'lua_code': '{var_name} = {value}'},
                {'type': 'variable', 'title': 'Get Variable', 'icon': '📖',
                'description': 'Get variable value',
                'lua_code': '{var_name}'},
                {'type': 'variable', 'title': 'Increment', 'icon': '➕',
                'description': 'Increase variable by 1',
                'lua_code': '{var_name} = {var_name} + 1'},
                {'type': 'variable', 'title': 'Decrement', 'icon': '➖',
                'description': 'Decrease variable by 1',
                'lua_code': '{var_name} = {var_name} - 1'},
            ],
            'Math': [
                {'type': 'operator', 'title': 'Add', 'icon': '+',
                'description': 'Addition operator',
                'lua_code': '{a} + {b}'},
                {'type': 'operator', 'title': 'Subtract', 'icon': '-',
                'description': 'Subtraction operator',
                'lua_code': '{a} - {b}'},
                {'type': 'operator', 'title': 'Multiply', 'icon': '×',
                'description': 'Multiplication operator',
                'lua_code': '{a} * {b}'},
                {'type': 'operator', 'title': 'Divide', 'icon': '÷',
                'description': 'Division operator',
                'lua_code': '{a} / {b}'},
                {'type': 'operator', 'title': 'Modulo', 'icon': '%',
                'description': 'Modulo operator',
                'lua_code': '{a} % {b}'},
                {'type': 'operator', 'title': 'Power', 'icon': '^',
                'description': 'Exponentiation',
                'lua_code': '{a} ^ {b}'},
                {'type': 'operator', 'title': 'Equal', 'icon': '=',
                'description': 'Equality comparison',
                'lua_code': '{a} == {b}'},
                {'type': 'operator', 'title': 'Not Equal', 'icon': '≠',
                'description': 'Inequality comparison',
                'lua_code': '{a} ~= {b}'},
            ],
            'Quantum': [
                {'type': 'function', 'title': 'Quantum State', 'icon': '⚛️',
                'description': 'Create quantum state',
                'lua_code': 'quantum_state({n_qubits})'},
                {'type': 'function', 'title': 'Apply Gate', 'icon': '🔷',
                'description': 'Apply quantum gate',
                'lua_code': 'apply_gate({state}, "{gate}", {qubit})'},
                {'type': 'function', 'title': 'Measure', 'icon': '📏',
                'description': 'Measure quantum state',
                'lua_code': 'measure({state})'},
                {'type': 'function', 'title': 'Hadamard Gate', 'icon': 'H',
                'description': 'Apply Hadamard gate',
                'lua_code': 'apply_gate({state}, "H", {qubit})'},
                {'type': 'function', 'title': 'CNOT Gate', 'icon': '⊕',
                'description': 'Apply CNOT gate',
                'lua_code': 'apply_gate({state}, "CNOT", {control}, {target})'},
                {'type': 'function', 'title': 'Quantum Circuit', 'icon': '🔗',
                'description': 'Create quantum circuit',
                'lua_code': '-- Quantum circuit initialization\nlocal circuit = {}\nprint("Quantum circuit created")'},
            ],
            'Input/Output': [
                {'type': 'function', 'title': 'Print', 'icon': '🖨️',
                'description': 'Print to console',
                'lua_code': 'print("{message}")'},
                {'type': 'function', 'title': 'Read Input', 'icon': '📥',
                'description': 'Read user input',
                'lua_code': 'local input = io.read()'},
                {'type': 'function', 'title': 'Read File', 'icon': '📄',
                'description': 'Read from file',
                'lua_code': 'local file = io.open("{filename}", "r")\nlocal content = file:read("*a")\nfile:close()'},
                {'type': 'function', 'title': 'Write File', 'icon': '📝',
                'description': 'Write to file',
                'lua_code': 'local file = io.open("{filename}", "w")\nfile:write("{content}")\nfile:close()'},
            ]
        }
        return blocks
    
    def _setup_ui(self):
        """Setup the block library UI"""
        for category, block_list in self.blocks.items():
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setSpacing(5)
            
            for block_data in block_list:
                btn = QPushButton(f"{block_data.get('icon', '▢')} {block_data['title']}")
                btn.setToolTip(block_data['description'])
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 6px;
                        margin: 1px;
                        border: 1px solid #ddd;
                        border-radius: 3px;
                        background-color: white;
                    }
                    QPushButton:hover {
                        background-color: #f0f0f0;
                        border-color: #3498db;
                    }
                """)
                
                # Store block data
                btn.block_data = block_data
                btn.clicked.connect(lambda checked, b=btn: self._on_block_clicked(b))
                
                layout.addWidget(btn)
            
            layout.addStretch()
            self.addItem(widget, category)
    
    def _on_block_clicked(self, button):
        """Handle block selection"""
        self.block_selected.emit(button.block_data)


class CodePreviewWidget(QTextEdit):
    """Widget for previewing generated Lua code"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
            }
        """)
    
    def update_code(self, code: str):
        """Update displayed code"""
        self.setPlainText(code)
        
        # Move cursor to top
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self.setTextCursor(cursor)