"""
VS Code Write Skill (Human Simulation Mode)
拟人化模式：模拟人类操作 VS Code 进行代码编写
"""

import time
import subprocess
import os
import platform
import pyautogui
import pyperclip
from skills.base import Skill

class VSCodeWriteSkill(Skill):
    def __init__(self):
        super().__init__()
        self.name = "vscode_write"
        self.description = """
        【拟人操作】使用 VS Code 编辑器写入代码。
        Agent 会模拟人类动作：打开编辑器 -> 聚焦窗口 -> 粘贴代码 -> 保存文件。
        注意：执行期间请勿触碰鼠标键盘。
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "文件名 (例如: game.py)"
                },
                "code": {
                    "type": "string",
                    "description": "完整的代码内容"
                }
            },
            "required": ["filename", "code"]
        }

    def _wait_for_file_save(self, filename, timeout=5):
        """等待文件被写入（闭环检测）"""
        start = time.time()
        while time.time() - start < timeout:
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return True
            time.sleep(0.5)
        return False

    def execute(self, filename, code, **kwargs) -> str:
        # 参数容错
        filename = filename or kwargs.get('file') or kwargs.get('file_name')
        code = code or kwargs.get('content')
        
        if not filename: return "❌ 错误: 缺少文件名"
        
        # 1. 物理创建空文件 (为了让 VS Code 有东西可开)
        # 这一步是必须的，否则 code 命令可能会打开一个未保存的 Tab
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("") # 创建空文件

        try:
            # 2. 【拟人动作】调用系统命令打开 VS Code
            # 这相当于人类双击文件，系统会自动聚焦到 VS Code 窗口
            print(f"🖥️ [GUI] 正在唤起 VS Code: {filename}")
            if platform.system() == "Windows":
                subprocess.Popen(f'code "{filename}"', shell=True)
            else:
                subprocess.Popen(["code", filename])
            
            # 【关键】给 VS Code 启动和渲染留足时间
            # Manus 之所以稳，是因为它看屏幕。我们这里盲打，必须给足 Buffer。
            time.sleep(3) 

            # 3. 【拟人动作】写入代码
            # 使用剪贴板 + 粘贴 (模拟人类的高效操作，比 typewrite 一个个敲字稳)
            pyperclip.copy(code)
            time.sleep(0.5) # 等待剪贴板写入

            # 激活编辑区 (防止焦点在侧边栏)
            pyautogui.click(pyautogui.size().width // 2, pyautogui.size().height // 2)
            
            # 全选 -> 清空 -> 粘贴 -> 保存
            print("⌨️ [GUI] 正在输入代码...")
            
            # 全选 (Ctrl+A)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5)
            
            # 粘贴 (Ctrl+V)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1.0) # 等待大段文本粘贴完成
            
            # 保存 (Ctrl+S)
            print("💾 [GUI] 保存文件...")
            pyautogui.hotkey('ctrl', 's')
            time.sleep(1.0) # 等待磁盘写入

            # 4. 【闭环验证】检查到底写进去没
            # 这是 Moltbot/Manus 的核心逻辑：操作完必须看一眼结果
            if self._wait_for_file_save(filename):
                size = os.path.getsize(filename)
                return f"✅ 代码已通过 VS Code 写入 {filename} (大小: {size} bytes)。"
            else:
                return f"VS Code 已打开，但文件 {filename} 仍然是空的 (0 bytes)。可能焦点丢失或保存快捷键未生效。请尝试重新执行。"

        except Exception as e:
            return f"❌ GUI 操作异常: {str(e)}"