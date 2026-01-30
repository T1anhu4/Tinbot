"""
Vision Engine (Qwen-VL / OpenAI / Gemini)
视觉中枢 - 让 Agent 长出眼睛
"""

import pyautogui
import base64
import time
import json
from io import BytesIO
from PIL import Image

class VisionEngine:
    def __init__(self, llm_client, model_name="qwen-vl-max"):
        self.llm = llm_client
        self.model_name = model_name
        print(f"[Vision] 视觉引擎初始化: {model_name}")

    def _capture_screen_b64(self):
        """截图并转为 base64 (省钱版)"""
        try:
            screenshot = pyautogui.screenshot()
            screenshot = screenshot.convert('RGB')
            
            # 【优化】将分辨率限制在 768px (足够看清UI，但Token少很多)
            # 如果觉得看不清字，可以改成 1024，但 768 是性价比之选
            max_size = 768 
            if max(screenshot.size) > max_size:
                screenshot.thumbnail((max_size, max_size))
            
            buffered = BytesIO()
            # 【优化】JPEG 质量降到 50 (人类看着有噪点，但 AI 识别文字足够了)
            screenshot.save(buffered, format="JPEG", quality=50)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return img_str
        except Exception as e:
            print(f"❌ 截图失败: {e}")
            return None

    def see_and_think(self, prompt="描述当前屏幕内容"):
        """
        看一眼屏幕，并回答问题
        """
        b64_img = self._capture_screen_b64()
        if not b64_img: return "无法获取屏幕图像"

        try:
            # 构造多模态请求 (适配 OpenAI / Qwen 格式)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]

            response = self.llm.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=300 # 不需要太长
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"视觉分析出错: {e}"

    def verify_action(self, last_action, last_target):
        """
        【视觉闭环核心】验证刚才的操作是否生效
        """
        prompt = f"""
        我刚才执行了操作：【{last_action} {last_target}】。
        请看当前屏幕截图，简要回答：
        1. 当前活动窗口是什么？
        2. 操作看起来成功了吗？(例如：如果我要打开浏览器，现在看到浏览器窗口了吗？)
        
        请用一句话概括状态。例如："当前是Chrome窗口，操作成功。" 或 "未看到计算器，可能启动失败。"
        """
        return self.see_and_think(prompt)