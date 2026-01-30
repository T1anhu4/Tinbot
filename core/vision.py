import pyautogui
import base64
import time
import json
import re
from io import BytesIO

class VisionEngine:
    def __init__(self, llm_client, model_name="qwen-vl-max"):
        self.llm = llm_client
        self.model_name = model_name
        print(f"视觉引擎已就绪 ({model_name})")

    def capture_screen(self):
        screenshot = pyautogui.screenshot()
        buffered = BytesIO()
        screenshot.save(buffered, format="JPEG", quality=70)
        return base64.b64encode(buffered.getvalue()).decode()

    def analyze_ui(self, prompt):
        """简单的视觉分析接口"""
        b64_img = self.capture_screen()
        try:
            response = self.llm.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"视觉分析出错: {e}"