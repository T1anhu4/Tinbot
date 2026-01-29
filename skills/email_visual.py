from .base import Skill
import time 
import pyautogui
import pyperclip # 必须引入这个处理中文

class EmailVisualSkill(Skill):
    # 注意：vision_engine 应该在初始化时由 Agent 传入
    def __init__(self, vision_engine):
        super().__init__()
        self.name = "email_visual"
        self.vision = vision_engine # 接收外部传入的引擎实例
        
        self.description = """
        视觉邮件处理技能。
        支持：读取收件箱、撰写新邮件。
        注意：请确保邮件客户端已经打开并处于前台。
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["read_inbox", "compose_new"],
                    "description": "操作意图"
                },
                "recipient": {
                    "type": "string",
                    "description": "收件人邮箱 (仅发信时需要)"
                },
                "content": {
                    "type": "string",
                    "description": "邮件正文内容 (仅发信时需要)"
                }
            },
            "required": ["intent"]
        }

    def _type_text_robust(self, text):
        """内部辅助函数：鲁棒的文本输入（支持中文）"""
        pyperclip.copy(text)
        time.sleep(0.1) # 等待剪贴板写入
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.5) # 等待粘贴完成

    def execute(self, intent, recipient=None, content=None):
        
        if intent == "read_inbox":
            print("👀 [VisualEmail] 正在扫描收件箱...")
            # 让 LLM 直接通过截图阅读
            result = self.vision.analyze_ui("请详细阅读屏幕列表中的最新3封邮件，返回发件人和标题的摘要。")
            return f"📧 视觉读取结果:\n{result['text_content']}"

        elif intent == "compose_new":
            if not recipient or not content:
                return "❌ 错误：撰写邮件必须提供收件人(recipient)和内容(content)。"

            try:
                # 1. 点击写信按钮
                print("👀 [VisualEmail] 寻找写信入口...")
                self.vision.click_element("写信(Compose) 或 新建邮件 按钮")
                time.sleep(2) # 等待弹窗动画

                # 2. 定位收件人并输入
                print("👀 [VisualEmail] 定位收件人栏...")
                self.vision.click_element("收件人输入框") 
                self._type_text_robust(recipient)
                
                # 3. 定位正文并输入
                print("👀 [VisualEmail] 定位正文栏...")
                # 这里有个技巧：有时候点正文需要避开标题栏，描述要准确
                self.vision.click_element("邮件正文编辑区域")
                self._type_text_robust(content)

                return f"✅ 邮件已填写完毕。\n收件人: {recipient}\n内容已粘贴。\n⚠️ 下一步请调用 'click_element' 点击发送按钮。"
            
            except Exception as e:
                return f"❌ 视觉操作执行失败: {str(e)}"

        return "❌ 未知指令"