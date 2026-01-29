import pyautogui
import base64
import time
import json
from io import BytesIO

class VisionEngine:
    def __init__(self, llm_client):
        self.llm = llm_client
        # 获取屏幕分辨率，用于坐标转换
        self.screen_width, self.screen_height = pyautogui.size()

    def capture_screen(self):
        """截取当前屏幕并转Base64"""
        screenshot = pyautogui.screenshot()
        buffered = BytesIO()
        screenshot.save(buffered, format="JPEG", quality=70)
        return base64.b64encode(buffered.getvalue()).decode(), screenshot.size

    def analyze_ui(self, prompt_instruction):
        """
        核心视觉能力
        """
        b64_img, size = self.capture_screen()
        
        print(f"👁️ [VisionEngine] 正在思考: {prompt_instruction}...")
        
        # --- 真实场景下的伪代码 ---
        # response = self.llm.chat(
        #     image=b64_img,
        #     prompt=f"{prompt_instruction} 请以JSON格式返回，包含 'action', 'coordinates': [x, y] (0-1000归一化坐标), 'text_content'."
        # )
        # data = json.loads(response)
        
        # --- 模拟返回 (Mock) ---
        # 假设我们让模型总是返回 0-1000 的归一化坐标，这样不受分辨率影响
        return {
            "action": "click",
            "norm_coordinates": [500, 300], # 假设模型认为目标在屏幕中心
            "text_content": "这里是模拟的屏幕文字识别结果..."
        }

    def click_element(self, element_description, double_click=False):
        """通用原子操作：找 -> 算坐标 -> 点"""
        result = self.analyze_ui(f"请找到屏幕上的UI元素 '{element_description}' 的中心点位置。")
        
        # 解析归一化坐标 [x, y] (范围0-1000) 转为 实际像素
        norm_x, norm_y = result["norm_coordinates"]
        real_x = int(norm_x / 1000 * self.screen_width)
        real_y = int(norm_y / 1000 * self.screen_height)

        pyautogui.moveTo(real_x, real_y, duration=0.5)
        
        if double_click:
            pyautogui.doubleClick()
        else:
            pyautogui.click()
            
        return f"✅ 已点击 {element_description} (坐标: {real_x}, {real_y})"