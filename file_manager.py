"""
file_manager.py - File management for Lua block projects
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
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class LuaFileManager:
    """Manager for Lua file operations"""
    
    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path.home() / "LuaBlockProjects"
        self.project_dir.mkdir(parents=True, exist_ok=True)
        
        self.exports_dir = self.project_dir / "exports"
        self.exports_dir.mkdir(exist_ok=True)
        
        self.templates_dir = self.project_dir / "templates"
        self.templates_dir.mkdir(exist_ok=True)
    
    def save_lua_file(self, code: str, filename: str, 
                     engine: str = "lua", 
                     export_dir: Optional[Path] = None) -> Path:
        """Save Lua code to file with proper headers"""
        if export_dir:
            save_dir = export_dir
        else:
            save_dir = self.exports_dir / engine
            save_dir.mkdir(exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_stem = Path(filename).stem
        full_filename = f"{file_stem}_{timestamp}.lua"
        
        file_path = save_dir / full_filename
        
        # Add engine-specific headers
        headers = self._get_engine_headers(engine)
        complete_code = headers + "\n\n" + code
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(complete_code)
        
        return file_path
    
    def _get_engine_headers(self, engine: str) -> str:
        """Get headers for specific Lua engine"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if engine.lower() == "luajit":
            return f"""-- LuaJIT Code
-- Generated: {timestamp}
-- Engine: LuaJIT 2.1.0-beta3
-- Platform: {self._get_platform_info()}

-- LuaJIT specific optimizations
if jit then
    jit.on()
    print("LuaJIT JIT compiler enabled")
end
"""
        else:
            return f"""-- Lua Code
-- Generated: {timestamp}
-- Engine: Lua 5.4
-- Platform: {self._get_platform_info()}
"""
    
    def _get_platform_info(self) -> str:
        """Get platform information"""
        import sys
        import platform
        return f"{platform.system()} {platform.release()} ({sys.platform})"
    
    def save_project(self, blocks: List[Dict[str, Any]], 
                    settings: Dict[str, Any], 
                    filename: str) -> Path:
        """Save complete project"""
        project_data = {
            'version': '2.0',
            'blocks': blocks,
            'engine_settings': settings,
            'metadata': {
                'name': filename,
                'created': datetime.now().isoformat(),
                'blocks_count': len(blocks),
                'engine': settings.get('engine', 'lua')
            }
        }
        
        file_path = self.project_dir / f"{filename}.blockproj"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2)
        
        return file_path
    
    def load_project(self, filepath: Path) -> Dict[str, Any]:
        """Load project from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    
    def export_project(self, project_data: Dict[str, Any], 
                      export_format: str = "zip") -> Path:
        """Export project in various formats"""
        if export_format == "zip":
            return self._export_as_zip(project_data)
        else:
            return self._export_as_folder(project_data)
    
    def _export_as_zip(self, project_data: Dict[str, Any]) -> Path:
        """Export project as ZIP file"""
        import zipfile
        
        # Create temp directory
        temp_dir = self.exports_dir / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        project_name = project_data['metadata']['name']
        export_dir = temp_dir / project_name
        export_dir.mkdir(exist_ok=True)
        
        # Save project file
        project_file = export_dir / f"{project_name}.blockproj"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2)
        
        # Generate and save Lua code
        if 'generated_code' in project_data:
            lua_file = export_dir / f"{project_name}.lua"
            with open(lua_file, 'w', encoding='utf-8') as f:
                f.write(project_data['generated_code'])
        
        # Create ZIP
        zip_path = self.exports_dir / f"{project_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in export_dir.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(temp_dir)
                    zipf.write(file, arcname)
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return zip_path