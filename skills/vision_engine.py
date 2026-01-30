"""
Vision Engine - 支持多种多模态 API
支持：OpenAI GPT-4o, Qwen-VL-MAX, Google Gemini, Anthropic Claude
"""

import pyautogui
import base64
import time
import json
import re
from io import BytesIO
from PIL import Image


class VisionEngine:
    """
    视觉引擎
    功能：截图、分析 UI、定位元素、点击操作
    支持多种多模态 API
    """
    
    def __init__(self, llm_client, model_name="qwen-vl-max", api_type="qwen"):
        """
        初始化视觉引擎
        
        Args:
            llm_client: API 客户端实例 (OpenAI 兼容格式)
            model_name: 模型名称
            api_type: API 类型 ("openai", "qwen", "gemini", "anthropic")
        """
        self.llm = llm_client
        self.model_name = model_name
        self.api_type = api_type.lower()
        self.screen_width, self.screen_height = pyautogui.size()
        
        # 视觉缓存
        self.last_screenshot = None
        self.last_screenshot_time = 0
        self.cache_duration = 2  # 缓存2秒
        
        print(f"[VisionEngine] 初始化完成")
        print(f"  模型: {model_name}")
        print(f"  API类型: {api_type}")
    
    def capture_screen(self, use_cache=True):
        """
        截取当前屏幕并转 Base64
        
        Args:
            use_cache: 是否使用缓存
            
        Returns:
            tuple: (base64字符串, 图片尺寸)
        """
        # 检查缓存
        if use_cache and self.last_screenshot:
            if time.time() - self.last_screenshot_time < self.cache_duration:
                return self.last_screenshot
        
        # 截图
        screenshot = pyautogui.screenshot()
        
        # 压缩图片（降低 token 消耗）
        screenshot.thumbnail((1280, 720), Image.Resampling.LANCZOS)
        
        # 转 Base64
        buffered = BytesIO()
        screenshot.save(buffered, format="JPEG", quality=85)
        b64_img = base64.b64encode(buffered.getvalue()).decode()
        
        # 更新缓存
        self.last_screenshot = (b64_img, screenshot.size)
        self.last_screenshot_time = time.time()
        
        return b64_img, screenshot.size
    
    def _call_qwen_vision(self, b64_img, prompt):
        """
        调用 Qwen-VL-MAX (通义千问多模态)
        
        Qwen-VL 使用 OpenAI 兼容的 API 格式
        """
        system_prompt = """你是一个专业的 UI 视觉分析助手。
你的任务是分析屏幕截图并定位 UI 元素。

**返回格式（严格 JSON）:**
{
    "action": "click",
    "coordinates": [x, y],
    "text_content": "识别到的文字内容",
    "confidence": 0.95
}

**重要说明:**
- coordinates 必须是归一化坐标，范围 0-1
- [0, 0] 代表左上角
- [1, 1] 代表右下角
- [0.5, 0.5] 代表屏幕正中心
- 请务必返回纯 JSON，不要包含任何额外的文字说明
"""
        
        # Qwen-VL-MAX 的消息格式
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_img}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
        
        try:
            response = self.llm.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=1000,
                temperature=0.1
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            print(f"Qwen-VL API 调用失败: {e}")
            raise
    
    def analyze_ui(self, prompt_instruction, use_cache=True):
        """
        分析 UI 界面
        
        Args:
            prompt_instruction: 指令
            use_cache: 是否使用缓存
            
        Returns:
            dict: 分析结果
        """
        b64_img, img_size = self.capture_screen(use_cache)
        
        print(f"[VisionEngine] 正在分析: {prompt_instruction}...")
        
        try:
            # 调用 Qwen-VL
            content = self._call_qwen_vision(b64_img, prompt_instruction)
            
            # 解析 JSON
            result = self._parse_vision_response(content)
            
            if result["confidence"] < 0.5:
                print(f"[VisionEngine] 低置信度: {result['confidence']}")
            
            return result
        
        except Exception as e:
            print(f"[VisionEngine] 视觉分析失败: {e}")
            return {
                "action": "error",
                "coordinates": [0.5, 0.5],
                "text_content": f"分析失败: {str(e)}",
                "confidence": 0
            }
    
    def _parse_vision_response(self, content):
        """解析 LLM 的视觉响应"""
        try:
            # 清洗 JSON（移除 Markdown 包裹）
            content = re.sub(r'```json\s*|\s*```', '', content).strip()
            
            # 提取第一个完整的 JSON 对象
            start = content.find('{')
            if start != -1:
                stack = 0
                for i in range(start, len(content)):
                    if content[i] == '{':
                        stack += 1
                    elif content[i] == '}':
                        stack -= 1
                        if stack == 0:
                            json_str = content[start:i+1]
                            parsed = json.loads(json_str)
                            
                            # 验证必需字段
                            if "coordinates" not in parsed:
                                raise ValueError("缺少 coordinates 字段")
                            
                            # 设置默认值
                            if "confidence" not in parsed:
                                parsed["confidence"] = 0.8
                            if "text_content" not in parsed:
                                parsed["text_content"] = ""
                            if "action" not in parsed:
                                parsed["action"] = "click"
                            
                            return parsed
            
            raise ValueError("未找到有效的 JSON")
        
        except Exception as e:
            print(f"❌ JSON 解析失败: {e}")
            print(f"原始内容: {content[:200]}...")
            return {
                "action": "error",
                "coordinates": [0.5, 0.5],
                "text_content": content[:200],
                "confidence": 0
            }
    
    def click_element(self, element_description, double_click=False, retry=3):
        """
        点击 UI 元素
        
        Args:
            element_description: 元素描述
            double_click: 是否双击
            retry: 重试次数
        """
        for attempt in range(retry):
            try:
                result = self.analyze_ui(
                    f"请找到屏幕上的 '{element_description}' 并返回其中心点位置。",
                    use_cache=(attempt == 0)
                )
                
                if result["confidence"] < 0.5:
                    if attempt < retry - 1:
                        print(f"置信度过低，重试 ({attempt + 1}/{retry})...")
                        time.sleep(1)
                        continue
                    else:
                        return f"❌ 未找到元素: {element_description}"
                
                # 转换坐标
                norm_x, norm_y = result["coordinates"]
                real_x = int(norm_x * self.screen_width)
                real_y = int(norm_y * self.screen_height)
                
                # 边界检查
                real_x = max(0, min(real_x, self.screen_width - 1))
                real_y = max(0, min(real_y, self.screen_height - 1))
                
                # 移动并点击
                pyautogui.moveTo(real_x, real_y, duration=0.5)
                time.sleep(0.2)
                
                if double_click:
                    pyautogui.doubleClick()
                else:
                    pyautogui.click()
                
                return f"✅ 已点击 '{element_description}' (坐标: {real_x}, {real_y}, 置信度: {result['confidence']:.2f})"
            
            except Exception as e:
                if attempt < retry - 1:
                    print(f"❌ 点击失败，重试 ({attempt + 1}/{retry}): {e}")
                    time.sleep(1)
                else:
                    return f"❌ 点击失败: {str(e)}"
        
        return f"❌ 超过最大重试次数"
    
    def read_screen_text(self, area_description="整个屏幕"):
        """读取屏幕文字"""
        result = self.analyze_ui(
            f"请识别 {area_description} 上的所有文字内容，按从上到下、从左到右的顺序列出。"
        )
        
        return result.get("text_content", "")
    
    def find_element_position(self, element_description):
        """查找元素位置"""
        result = self.analyze_ui(f"请找到 '{element_description}' 的位置")
        
        if result["confidence"] > 0.5:
            norm_x, norm_y = result["coordinates"]
            real_x = int(norm_x * self.screen_width)
            real_y = int(norm_y * self.screen_height)
            return (real_x, real_y, result["confidence"])
        
        return None