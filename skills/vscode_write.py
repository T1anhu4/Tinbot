"""
VS Code Write Skill
通过 GUI 自动化将代码写入 VS Code
"""

import time
import subprocess
import ast
import os
import pyautogui
import pyperclip
import pygetwindow as gw
from skills.base import Skill


def print_log(role, msg):
    """临时日志函数（避免循环依赖）"""
    colors = {
        "Skill": "\033[97m",
        "Error": "\033[91m",
        "Reset": "\033[0m"
    }
    print(f"{colors.get(role, colors['Reset'])}[{role}] {msg}{colors['Reset']}")


class VSCodeWriteSkill(Skill):
    """
    Skill: VS Code 写代码
    功能: 通过 GUI 自动化将代码写入 VS Code
    """
    
    def __init__(self):
        super().__init__()
        self.name = "vscode_write"
        self.description = """
        使用 VS Code 编辑器写入代码文件。
        适用场景: 创建新的 Python 脚本、修改代码文件。
        注意: 必须提供完整的代码，不支持增量修改。
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "要创建/编辑的文件名 (如 game.py)"
                },
                "code": {
                    "type": "string",
                    "description": "完整的代码内容"
                }
            },
            "required": ["filename", "code"]
        }
    
    def _ensure_vscode_focused(self, filename: str) -> bool:
        """确保 VS Code 窗口处于激活状态"""
        subprocess.Popen(f'code "{filename}"', shell=True)
        time.sleep(2)
        
        target_window = None
        for _ in range(5):
            windows = gw.getWindowsWithTitle('Visual Studio Code')
            if windows:
                target_window = windows[0]
                break
            time.sleep(1)
        
        if not target_window:
            return False
        
        try:
            if target_window.isMinimized:
                target_window.restore()
            target_window.activate()
            time.sleep(0.5)
            return True
        except:
            return False
    
    def execute(self, code: str, filename: str = None, file: str = None) -> str:
        """
        执行写代码操作（支持 filename 或 file 参数）
        
        Args:
            code: 完整的代码内容
            filename: 文件名（推荐）
            file: 文件名（兼容参数）
            
        Returns:
            str: 执行结果
        """
        # 兼容两种参数名
        filename = filename or file
        if not filename:
            return "❌ 缺少文件名参数"
        
        print_log("Skill", f"[{self.name}] 正在写入文件: {filename}")
        
        # 1. 语法预检
        try:
            ast.parse(code)
        except SyntaxError as e:
            return f"❌ 语法错误 (Line {e.lineno}): {e.msg}"
        
        # 2. 物理文件创建
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("")
        
        # 3. VS Code 操作
        if self._ensure_vscode_focused(filename):
            # 聚焦编辑区
            pyautogui.hotkey('ctrl', '1')
            time.sleep(0.5)
            
            # 清空 + 粘贴
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.3)
            pyautogui.press('backspace')
            time.sleep(0.3)
            
            pyperclip.copy(code)
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1)
            
            # 格式化 + 保存
            pyautogui.hotkey('shift', 'alt', 'f')
            time.sleep(1)
            pyautogui.hotkey('ctrl', 's')
            time.sleep(0.5)
            
            return f"✅ 代码已写入 {filename} 并保存"
        else:
            return "❌ 无法聚焦 VS Code 窗口"