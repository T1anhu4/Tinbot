"""
Browser DOM Skill (DrissionPage Lightweight)
轻量级 DOM 浏览器 - 直接接管现有 Chrome/Edge，无需下载内核
"""
from skills.base import Skill
from DrissionPage import ChromiumPage, ChromiumOptions
import time

# 全局保持浏览器对象
PAGE = None

class BrowserDOMSkill(Skill):
    def __init__(self):
        super().__init__()
        self.name = "browser_dom"
        self.description = """
        【精准网页浏览】
        直接接管现有浏览器，基于 DOM 结构进行精准读取和点击。
        
        功能:
        1. open: 打开网址。
        2. get_state: 获取页面上的交互元素列表 (带ID)。
        3. click: 点击元素 (提供 ID 或 包含的文字)。
        4. type: 输入文字 (提供 ID 或 包含的文字)。
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["open", "get_state", "click", "type"]
                },
                "target": {
                    "type": "string",
                    "description": "网址、元素ID、或按钮上的文字"
                },
                "text": {
                    "type": "string",
                    "description": "输入的内容 (仅 type 用)"
                }
            },
            "required": ["action"]
        }

    def _init_browser(self):
        global PAGE
        if not PAGE:
            try:
                # 配置接管现有浏览器
                co = ChromiumOptions()
                # 自动寻找系统里的 Chrome/Edge
                co.auto_port() 
                # co.headless() # 如果想后台运行可以打开这个，但在桌面模式建议看着它跑
                
                PAGE = ChromiumPage(co)
                print("[Browser] 已连接到现有浏览器")
            except Exception as e:
                print(f"❌ 浏览器连接失败: {e}")

    def _simplify_dom(self):
        """
        将页面元素转化为 LLM 能看懂的简洁清单
        """
        if not PAGE: return "浏览器未启动"
        
        # 只提取主要交互元素：链接、按钮、输入框
        # DrissionPage 的语法非常简洁
        eles = PAGE.eles('tag:a') + PAGE.eles('tag:button') + PAGE.eles('tag:input')
        
        summary = []
        # 我们只取前 60 个可见元素，防止 Token 爆炸
        count = 0
        for ele in eles:
            if not ele.states.is_displayed: continue # 跳过看不见的
            
            # 获取文本或属性
            text = ele.text.strip()
            if not text:
                text = ele.attr('placeholder') or ele.attr('title') or ele.attr('aria-label') or ""
            
            # 如果实在没字，跳过 (输入框除外)
            if not text and ele.tag != 'input': continue
            
            # 生成描述
            # 格式: [ID] <标签> 文本内容
            # 这里的 ID 我们用元素的 xpath 或者 backend_id，为了给 LLM 方便，我们临时编个号
            # 但实际操作时，我们最好让 LLM 传“文本”回来，因为 DrissionPage 文本定位很强
            
            desc = f"[{count}] <{ele.tag}> {text[:30]}"
            if ele.tag == 'input':
                desc += " (输入框)"
            
            summary.append(desc)
            count += 1
            if count >= 60: break
            
        return "\n".join(summary)

    def execute(self, action, target=None, text=None, **kwargs) -> str:
        self._init_browser()
        if not PAGE: return "❌ 无法启动浏览器"

        try:
            if action == "open":
                print(f"[DOM] 访问: {target}")
                PAGE.get(target)
                return f"✅ 已访问 {target}"

            elif action == "get_state":
                dom_str = self._simplify_dom()
                return f"[当前页面元素清单]:\n{dom_str}\n\n👉 提示：请使用 'click' 动作，Target 填元素里的【文字】或【ID编号】。"

            elif action == "click":
                print(f"[DOM] 点击: {target}")
                # 1. 尝试当做数字 ID 处理
                if target.isdigit() and int(target) < 60:
                    # 重新获取一遍列表来定位 (略显低效但最稳)
                    # 实际使用中建议用 text 定位
                    pass 
                
                # 2. 核心：直接用文字模糊定位 (DrissionPage 强项)
                # 这比 ID 更符合人类直觉："点击 '搜索'"
                if PAGE.ele(f'{target}'):
                    PAGE.ele(f'{target}').click()
                    return f"✅ 已点击包含 '{target}' 的元素"
                else:
                    return f"❌ 未找到包含 '{target}' 的元素"

            elif action == "type":
                print(f"[DOM] 输入: {text} -> {target}")
                # 这里的 target 最好是输入框旁边的字，或者 placeholder
                # 比如：target="搜索", text="黑神话"
                ele = PAGE.ele(f'{target}')
                if ele:
                    ele.input(text)
                    PAGE.actions.type('ENTER') # 输完自动回车
                    return f"✅ 已在 '{target}' 中输入 '{text}' 并回车"
                else:
                    return f"❌ 找不到输入框 '{target}'"

        except Exception as e:
            return f"❌ 浏览器操作异常: {e}"