"""
Skills Package
自动导入所有可用的 Skills
"""

from skills.base import Skill
from skills.vscode_write import VSCodeWriteSkill
from skills.run_python_file import RunPythonSkill
from skills.list_files import ListFilesSkill

# 导出所有 Skills
__all__ = [
    'Skill',
    'VSCodeWriteSkill',
    'RunPythonSkill',
    'ListFilesSkill',
]