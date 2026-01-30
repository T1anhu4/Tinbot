"""
Computer Control Skill (Ultimate Input)
包含：智能搜索启动、组合键、防输入法干扰的文本输入
"""

import pyautogui
import pyperclip
import time
import platform
from skills.base import Skill

class ComputerControlSkill(Skill):
    def __init__(self):
        super().__init__()
        self.name = "computer_control"
        self.description = """
        GUI 控制增强版。
        
        【核心功能】:
        1. open_app: 启动应用 (Target=应用名)。
        2. browser_nav: 浏览器专用导航 (Target=网址或搜索词)。会自动聚焦地址栏->粘贴->回车。
        3. hotkey: 组合键 (Target="ctrl,c", "alt,tab", "ctrl,l" 等)。
        4. type_text: 文本输入 (Target=内容)。会自动使用粘贴模式，防止输入法干扰。
        5. mouse_click: 点击坐标 (Target="x,y")。
        6. scroll: 滚轮 (Target=正数向上/负数向下)。
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["open_app", "browser_nav", "hotkey", "type_text", "mouse_click", "scroll"],
                    "description": "操作类型"
                },
                "target": {
                    "type": "string",
                    "description": "目标内容"
                }
            },
            "required": ["action"]
        }

    def _is_mac(self):
        return platform.system() == "Darwin"

    def _paste_text(self, text):
        """核心：通过剪贴板粘贴文本（避开输入法）"""
        pyperclip.copy(text)
        time.sleep(0.1)
        if self._is_mac():
            pyautogui.hotkey('command', 'v')
        else:
            pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)

    def execute(self, action: str, target: str = None, **kwargs) -> str:
        action = kwargs.get('operation', action)
        target = kwargs.get('app_name', kwargs.get('browser', target))

        try:
            if action == "open_app":
                if not target: return "❌ 错误：缺少 target"
                print(f"[System] 搜索启动: {target}")
                
                # 呼出搜索框
                if self._is_mac():
                    pyautogui.hotkey('command', 'space')
                else:
                    pyautogui.press('win')
                
                time.sleep(0.5)
                self._paste_text(target) # 粘贴应用名
                time.sleep(1.0) 
                pyautogui.press('enter')
                time.sleep(3.0) # 给够时间启动
                return f"✅ 已启动: {target}"

            elif action == "browser_nav":
                if not target: return "❌ 错误：缺少网址或关键词"
                print(f"[Browser] 导航至: {target}")
                
                # 1. 聚焦地址栏 (Ctrl+L / Cmd+L)
                if self._is_mac():
                    pyautogui.hotkey('command', 'l')
                else:
                    pyautogui.hotkey('ctrl', 'l')
                time.sleep(0.5)
                
                # 2. 粘贴内容
                self._paste_text(target)
                
                # 3. 回车
                pyautogui.press('enter')
                return f"✅ 已在浏览器导航/搜索: {target}"

            elif action == "hotkey":
                # 解析 "ctrl,c" 或 "alt,tab"
                if not target: return "❌ 错误：缺少按键组合"
                keys = [k.strip().lower() for k in target.replace('，', ',').split(',')]
                print(f"[Hotkey] 按下: {'+'.join(keys)}")
                pyautogui.hotkey(*keys)
                return f"✅ 已按组合键: {target}"
            
            elif action == "type_text":
                if not target: return "❌ 错误：缺少内容"
                print(f"[Type] 粘贴输入: {target}")
                self._paste_text(target)
                # 这里的回车由 Agent 决定是否通过 hotkey 触发，或者纯输入
                return f"✅ 已输入文本: {target}"
            
            elif action == "mouse_click":
                try:
                    x, y = map(int, target.replace('，', ',').split(','))
                    print(f"[Click] 点击: {x}, {y}")
                    pyautogui.click(x, y)
                    return f"✅ 已点击 ({x}, {y})"
                except:
                    return "❌ 坐标错误，格式应为 'x,y'"

            elif action == "scroll":
                amount = int(target)
                pyautogui.scroll(amount)
                return f"✅ 已滚动: {amount}"
            
            else:
                return f"❌ 未知操作: {action}"
                
        except Exception as e:
            return f"❌ GUI异常: {str(e)}"