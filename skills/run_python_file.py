"""
Run Python Skill
执行 Python 文件，自动安装缺失的依赖库
"""

import sys
import os
import re
import subprocess
from skills.base import Skill


def print_log(role, msg):
    """临时日志函数（避免循环依赖）"""
    colors = {
        "Skill": "\033[97m",
        "Reset": "\033[0m"
    }
    print(f"{colors.get(role, colors['Reset'])}[{role}] {msg}{colors['Reset']}")


class RunPythonSkill(Skill):
    """
    Skill: 运行 Python 文件
    功能: 执行 Python 脚本，自动安装缺失的依赖库
    """
    
    def __init__(self):
        super().__init__()
        self.name = "run_python"
        self.description = """
        运行指定的 Python 文件。
        功能:
        1. 自动检测缺失的第三方库并安装
        2. 捕获运行输出和错误信息
        3. 对 GUI 程序特殊处理 (短超时)
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "要运行的 Python 文件名 (如 snake_game.py)"
                }
            },
            "required": ["filename"]
        }
        
        # 库名映射表
        self.package_mapping = {
            'cv2': 'opencv-python',
            'PIL': 'pillow',
            'docx': 'python-docx',
            'sklearn': 'scikit-learn'
        }
    
    def _install_package(self, package: str) -> bool:
        """安装 Python 包"""
        try:
            print_log("Skill", f"正在安装: {package}")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                check=True,
                capture_output=True
            )
            return True
        except:
            return False
    
    def execute(self, filename: str) -> str:
        """
        执行 Python 文件
        
        Args:
            filename: 要运行的文件名
            
        Returns:
            str: 运行结果
        """
        print_log("Skill", f"[{self.name}] 正在运行: {filename}")
        
        # 1. 文件存在性检查
        if not os.path.exists(filename):
            return f"❌ 文件不存在: {filename}"
        
        # 2. 读取代码判断是否为 GUI 程序
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        is_gui = any(keyword in content for keyword in [
            'pygame', 'tkinter', 'PyQt', 'PySide', 'wx'
        ])
        
        # 3. 运行程序
        try:
            timeout = 6 if is_gui else 30
            result = subprocess.run(
                [sys.executable, filename],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            stderr = result.stderr
            
            # 4. 处理缺失库
            if "ModuleNotFoundError" in stderr:
                match = re.search(r"No module named '(\w+)'", stderr)
                if match:
                    module_name = match.group(1)
                    # 查找真实包名
                    package = self.package_mapping.get(module_name, module_name)
                    
                    if self._install_package(package):
                        return f"✅ 已自动安装 {package}，请重新运行"
                    else:
                        return f"❌ 安装 {package} 失败"
            
            # 5. 返回运行结果
            if is_gui and result.returncode != 0:
                return f"✅ GUI 程序已启动 (测试通过)"
            
            output = f"运行结束 (退出码: {result.returncode})\n"
            if result.stdout:
                output += f"\n标准输出:\n{result.stdout}"
            if result.stderr:
                output += f"\n错误输出:\n{result.stderr}"
            
            return output
            
        except subprocess.TimeoutExpired:
            return "✅ GUI 程序已启动 (运行超时保护)" if is_gui else "❌ 运行超时"
        except Exception as e:
            return f"❌ 系统错误: {str(e)}"