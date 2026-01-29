import pyautogui
import time
import subprocess
from .base import Skill

class ComputerControlSkill(Skill):
    def __init__(self):
        super().__init__()
        self.name = "computer_control"
        self.description = "OS层级控制：打开软件、浏览器、窗口管理、系统设置。做具体业务(如发邮件)前先用我打开软件。"
        self.parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["open_app", "minimize_all", "scroll", "type_text"],
                    "description": "操作类型"
                },
                "target": {
                    "type": "string",
                    "description": "目标软件名或输入内容 (例如 'chrome', '网易云音乐')"
                }
            },
            "required": ["action"]
        }

    def execute(self, action, target=None):
        if action == "open_app":
            # Win 键搜索法，最通用
            pyautogui.press('win')
            time.sleep(0.5)
            pyautogui.write(target)
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(3) # 等待软件启动
            return f"✅ 已尝试打开应用: {target}"
            
        elif action == "minimize_all":
            pyautogui.hotkey('win', 'd')
            return "✅ 已最小化所有窗口"
            
        elif action == "scroll":
            # 向下滚动
            pyautogui.scroll(-500)
            return "✅ 已向下滚动页面"
        
        elif action == "type_text":
            # 这里的输入法是个大坑，建议用 pyperclip 粘贴法支持中文
            import pyperclip
            pyperclip.copy(target)
            pyautogui.hotkey('ctrl', 'v')
            return f"✅ 已输入文本: {target}"

        return "❌ 未知指令"