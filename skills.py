# ================= 新 Skill 示例 =================
# 演示如何快速扩展 Agent 能力

from agent import Skill
import subprocess
import os

# ================= SKILL 4: 安装 Python 包 =================

class InstallPackageSkill(Skill):
    """
    Skill: 安装 Python 包
    功能: 使用 pip 安装指定的 Python 第三方库
    """
    
    def __init__(self):
        super().__init__()
        self.name = "install_package"
        self.description = """
        使用 pip 安装 Python 第三方库。
        适用场景: 手动安装缺失的依赖、预装常用库。
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "package": {
                    "type": "string",
                    "description": "要安装的包名 (如 pygame, requests)"
                }
            },
            "required": ["package"]
        }
    
    def execute(self, package: str) -> str:
        """执行安装操作"""
        try:
            print(f"[install_package] 正在安装: {package}")
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return f"✅ 成功安装 {package}"
            else:
                return f"❌ 安装失败:\n{result.stderr}"
                
        except subprocess.TimeoutExpired:
            return f"❌ 安装超时 (>60s)"
        except Exception as e:
            return f"❌ 系统错误: {str(e)}"

# ================= SKILL 5: 读取文件内容 =================

class ReadFileSkill(Skill):
    """
    Skill: 读取文件内容
    功能: 读取指定文件的内容（用于调试/检查）
    """
    
    def __init__(self):
        super().__init__()
        self.name = "read_file"
        self.description = """
        读取指定文件的内容。
        适用场景: 检查代码是否写入正确、查看日志文件。
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "要读取的文件名"
                },
                "max_lines": {
                    "type": "integer",
                    "description": "最多读取的行数 (默认 50)",
                    "default": 50
                }
            },
            "required": ["filename"]
        }
    
    def execute(self, filename: str, max_lines: int = 50) -> str:
        """执行读取操作"""
        try:
            if not os.path.exists(filename):
                return f"❌ 文件不存在: {filename}"
            
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            if total_lines > max_lines:
                content = ''.join(lines[:max_lines])
                return f"📄 {filename} (显示前 {max_lines}/{total_lines} 行):\n\n{content}\n\n... (已省略 {total_lines - max_lines} 行)"
            else:
                content = ''.join(lines)
                return f"📄 {filename} ({total_lines} 行):\n\n{content}"
                
        except Exception as e:
            return f"❌ 读取失败: {str(e)}"

# ================= SKILL 6: 删除文件 =================

class DeleteFileSkill(Skill):
    """
    Skill: 删除文件
    功能: 删除指定的文件或清理临时文件
    """
    
    def __init__(self):
        super().__init__()
        self.name = "delete_file"
        self.description = """
        删除指定的文件。
        适用场景: 清理临时文件、删除错误的代码文件。
        注意: 此操作不可逆！
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "要删除的文件名"
                }
            },
            "required": ["filename"]
        }
    
    def execute(self, filename: str) -> str:
        """执行删除操作"""
        try:
            if not os.path.exists(filename):
                return f"❌ 文件不存在: {filename}"
            
            os.remove(filename)
            return f"✅ 已删除文件: {filename}"
            
        except Exception as e:
            return f"❌ 删除失败: {str(e)}"

# ================= 如何使用新 Skill =================

"""
在 agent_modular.py 中添加新 Skill 只需 3 步:

1. 导入新 Skill:
   from skill_examples import InstallPackageSkill, ReadFileSkill, DeleteFileSkill

2. 在 AgentBrain.__init__ 中注册:
   self.skill_manager.register(InstallPackageSkill())
   self.skill_manager.register(ReadFileSkill())
   self.skill_manager.register(DeleteFileSkill())

3. 运行！Agent 会自动识别新技能

示例任务:
- "帮我安装 numpy 和 pandas"
- "读取 snake_game.py 的内容检查是否正确"
- "删除 test.py 这个临时文件"
"""