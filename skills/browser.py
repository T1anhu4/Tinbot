"""
Browser Skill
专门用于网页浏览的技能，引导 Agent 进行“浏览-观察”循环
"""
from skills.base import Skill
import pyautogui
import time
import platform

class BrowserSkill(Skill):
    def __init__(self):
        super().__init__()
        self.name = "browser"
        self.description = """
        【网页浏览器】
        用于访问网站、查看 GitHub、Bilibili 等。
        
        功能:
        1. visit: 访问网址或搜索关键词。
           (会自动打开浏览器 -> 输入网址 -> 回车 -> 等待加载 -> **自动触发视觉观察**)
        2. scroll_down: 向下滚动浏览（当页面内容没显示全时使用）。
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["visit", "scroll_down"],
                    "description": "动作"
                },
                "target": {
                    "type": "string",
                    "description": "网址(URL) 或 搜索关键词"
                }
            },
            "required": ["action"]
        }

    def execute(self, action, target=None, **kwargs) -> str:
        # 复用 computer_control 的逻辑，但增加特定延时和引导
        cc = self.context.get('skill_manager').skills.get('computer_control')
        if not cc: return "❌ 依赖 computer_control 插件"

        if action == "visit":
            # 1. 打开浏览器并导航
            res = cc.execute("browser_nav", target=target)
            
            # 2. 智能等待加载 (Manus 体验)
            print("[Browser] 正在等待页面加载...")
            time.sleep(4.0) # 网页加载通常比较慢，多等一会
            
            # 3. 提示 Agent 下一步该干嘛
            return f"{res}\n✅ 页面已加载。\n👉 提示：请立刻观察屏幕(Vision)。如果内容不完整，请使用 browser scroll_down。"

        elif action == "scroll_down":
            print("[Browser] 向下滚动...")
            pyautogui.scroll(-800) # 向下滚一屏
            time.sleep(1.0)
            return "✅ 已向下滚动，请观察新出现的内容。"

        return "❌ 未知浏览器动作"