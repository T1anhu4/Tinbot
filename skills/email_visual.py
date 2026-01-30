"""
Email Visual Skill
视觉邮件处理技能 - 基于多模态视觉理解
"""

import time
import pyautogui
import pyperclip
from skills.base import Skill


class EmailVisualSkill(Skill):
    """
    视觉邮件技能
    功能：读取收件箱、撰写邮件、发送邮件
    依赖：VisionEngine
    """
    
    def __init__(self, vision_engine=None):
        """
        初始化邮件技能
        
        Args:
            vision_engine: VisionEngine 实例（可选，支持延迟注入）
        """
        super().__init__()
        self.name = "email_visual"
        self.vision = vision_engine
        
        self.description = """
        视觉邮件处理技能。
        支持操作：
        1. read_inbox: 读取收件箱（识别最新邮件）
        2. compose_email: 撰写新邮件
        3. send_email: 点击发送按钮
        4. read_email_content: 读取当前打开的邮件内容
        
        注意事项：
        - 使用前请确保邮件客户端/网页已打开并处于前台
        - 支持 Outlook、网易邮箱、Gmail 等主流邮箱
        - 撰写邮件后需要手动调用 send_email 发送
        """
        
        self.parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "read_inbox",
                        "compose_email",
                        "send_email",
                        "read_email_content"
                    ],
                    "description": "操作类型"
                },
                "recipient": {
                    "type": "string",
                    "description": "收件人邮箱（compose_email 时必需）"
                },
                "subject": {
                    "type": "string",
                    "description": "邮件主题（compose_email 时可选）"
                },
                "content": {
                    "type": "string",
                    "description": "邮件正文（compose_email 时必需）"
                }
            },
            "required": ["action"]
        }
    
    def set_vision_engine(self, vision_engine):
        """
        延迟注入 VisionEngine（支持在 AgentBrain 中统一管理）
        
        Args:
            vision_engine: VisionEngine 实例
        """
        self.vision = vision_engine
    
    def _type_text_robust(self, text):
        """
        鲁棒的文本输入（支持中文）
        
        Args:
            text: 要输入的文本
        """
        pyperclip.copy(text)
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.5)
    
    def _check_vision_ready(self):
        """检查视觉引擎是否就绪"""
        if not self.vision:
            raise RuntimeError(
                "❌ VisionEngine 未初始化！\n"
                "请在 AgentBrain 中调用: email_skill.set_vision_engine(vision_engine)"
            )
    
    def execute(self, action: str, recipient: str = None, subject: str = None, content: str = None) -> str:
        """
        执行邮件操作
        
        Args:
            action: 操作类型
            recipient: 收件人
            subject: 主题
            content: 正文
            
        Returns:
            str: 执行结果
        """
        try:
            self._check_vision_ready()
            
            if action == "read_inbox":
                return self._read_inbox()
            
            elif action == "compose_email":
                if not recipient or not content:
                    return "❌ 错误：撰写邮件必须提供 recipient（收件人）和 content（正文）"
                return self._compose_email(recipient, subject, content)
            
            elif action == "send_email":
                return self._send_email()
            
            elif action == "read_email_content":
                return self._read_email_content()
            
            else:
                return f"❌ 未知操作: {action}"
        
        except Exception as e:
            return f"❌ 执行失败: {str(e)}"
    
    def _read_inbox(self) -> str:
        """读取收件箱"""
        print("👀 [EmailVisual] 正在扫描收件箱...")
        
        # 让视觉引擎读取收件箱列表
        result = self.vision.analyze_ui(
            "请识别邮件列表中最新的 3-5 封邮件，"
            "返回每封邮件的：发件人、主题、时间。"
            "如果看到未读标记，请注明。"
        )
        
        text_content = result.get("text_content", "")
        confidence = result.get("confidence", 0)
        
        if confidence < 0.5:
            return f"⚠️ 识别置信度较低 ({confidence:.2f})，可能不准确\n\n{text_content}"
        
        return f"📧 收件箱内容:\n\n{text_content}\n\n(置信度: {confidence:.2f})"
    
    def _compose_email(self, recipient: str, subject: str, content: str) -> str:
        """撰写新邮件"""
        print("📝 [EmailVisual] 开始撰写邮件...")
        
        steps_log = []
        
        try:
            # 步骤 1: 点击写信按钮
            print("👀 步骤 1/4: 寻找写信入口...")
            compose_keywords = [
                "写信", "写邮件", "撰写", "Compose", "New Email",
                "新建邮件", "New Message", "Write"
            ]
            
            compose_result = None
            for keyword in compose_keywords:
                result = self.vision.click_element(keyword, retry=1)
                if "✅" in result:
                    compose_result = result
                    break
            
            if not compose_result:
                return "❌ 未找到写信按钮，请确认邮件界面已打开"
            
            steps_log.append(compose_result)
            time.sleep(2)  # 等待弹窗
            
            # 步骤 2: 填写收件人
            print("👀 步骤 2/4: 填写收件人...")
            recipient_result = self.vision.click_element("收件人输入框")
            steps_log.append(recipient_result)
            time.sleep(0.5)
            
            self._type_text_robust(recipient)
            time.sleep(0.5)
            
            # 步骤 3: 填写主题（可选）
            if subject:
                print("👀 步骤 3/4: 填写主题...")
                subject_result = self.vision.click_element("主题输入框")
                steps_log.append(subject_result)
                time.sleep(0.5)
                
                self._type_text_robust(subject)
                time.sleep(0.5)
            else:
                steps_log.append("⏭️ 跳过主题（未提供）")
            
            # 步骤 4: 填写正文
            print("👀 步骤 4/4: 填写正文...")
            body_keywords = ["正文", "邮件正文", "编辑区域", "Message body", "邮件内容"]
            
            body_result = None
            for keyword in body_keywords:
                result = self.vision.click_element(keyword, retry=1)
                if "✅" in result:
                    body_result = result
                    break
            
            if not body_result:
                # 尝试按 Tab 键跳转到正文
                pyautogui.press('tab')
                time.sleep(0.3)
                body_result = "⚠️ 未找到正文框，已尝试 Tab 键跳转"
            
            steps_log.append(body_result)
            time.sleep(0.5)
            
            self._type_text_robust(content)
            time.sleep(1)
            
            # 生成总结
            summary = "\n".join([f"  {i+1}. {log}" for i, log in enumerate(steps_log)])
            
            return (
                f"✅ 邮件撰写完成\n\n"
                f"收件人: {recipient}\n"
                f"主题: {subject or '(无)'}\n"
                f"正文: {content[:50]}{'...' if len(content) > 50 else ''}\n\n"
                f"执行步骤:\n{summary}\n\n"
                f"⚠️ 下一步请调用 send_email 或手动点击发送按钮"
            )
        
        except Exception as e:
            return f"❌ 撰写失败: {str(e)}\n已完成步骤:\n" + "\n".join(steps_log)
    
    def _send_email(self) -> str:
        """点击发送按钮"""
        print("📤 [EmailVisual] 正在发送邮件...")
        
        # 多种发送按钮的可能文字
        send_keywords = [
            "发送", "Send", "发送邮件", "发 送", "Send Email"
        ]
        
        for keyword in send_keywords:
            result = self.vision.click_element(keyword, retry=2)
            if "✅" in result:
                return f"✅ 邮件已发送\n{result}"
        
        return (
            "⚠️ 未找到发送按钮，请手动点击发送\n"
            "提示：发送按钮通常在窗口底部或顶部"
        )
    
    def _read_email_content(self) -> str:
        """读取当前打开的邮件内容"""
        print("👀 [EmailVisual] 正在读取邮件内容...")
        
        result = self.vision.analyze_ui(
            "请识别当前邮件的：发件人、收件人、主题、正文内容。"
            "按格式返回：\n"
            "发件人: xxx\n"
            "主题: xxx\n"
            "正文: xxx"
        )
        
        text_content = result.get("text_content", "")
        confidence = result.get("confidence", 0)
        
        if confidence < 0.5:
            return f"⚠️ 识别置信度较低 ({confidence:.2f})\n\n{text_content}"
        
        return f"📧 邮件内容:\n\n{text_content}"