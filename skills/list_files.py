"""
List Files Skill
列出当前目录下的所有文件
"""

import os
from skills.base import Skill


def print_log(role, msg):
    """临时日志函数（避免循环依赖）"""
    colors = {
        "Skill": "\033[97m",
        "Reset": "\033[0m"
    }
    print(f"{colors.get(role, colors['Reset'])}[{role}] {msg}{colors['Reset']}")


class ListFilesSkill(Skill):
    """
    Skill: 列出当前目录文件
    功能: 查看当前工作目录下的所有文件
    """
    
    def __init__(self):
        super().__init__()
        self.name = "list_files"
        self.description = """
        列出当前工作目录下的所有文件和文件夹。
        适用场景: 查看有哪些文件、确认文件是否存在。
        """
        self.parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def execute(self) -> str:
        """
        列出当前目录文件
        
        Returns:
            str: 文件列表（格式化字符串）
        """
        print_log("Skill", f"[{self.name}] 正在列出当前目录文件")
        
        try:
            files = os.listdir('.')
            
            # 分类
            python_files = [f for f in files if f.endswith('.py')]
            other_files = [f for f in files if not f.endswith('.py')]
            
            result = "📂 当前目录文件列表:\n\n"
            
            if python_files:
                result += "🐍 Python 文件:\n"
                for f in python_files:
                    size = os.path.getsize(f)
                    result += f"  - {f} ({size} bytes)\n"
            
            if other_files:
                result += "\n📄 其他文件:\n"
                for f in other_files:
                    if os.path.isdir(f):
                        result += f"  - {f}/ (文件夹)\n"
                    else:
                        size = os.path.getsize(f)
                        result += f"  - {f} ({size} bytes)\n"
            
            return result if files else "当前目录为空"
            
        except Exception as e:
            return f"❌ 读取失败: {str(e)}"