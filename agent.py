import time
import re
import json
import traceback
from openai import OpenAI
from core.config import settings
from core.skill_manager import SkillManager
from core.vision import VisionEngine
from core.state import StateManager
from core.logger import log 

def extract_json(content):
    """尝试多种方式提取 JSON"""
    try:
        # 1. 优先匹配 Markdown 代码块 ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if match: return json.loads(match.group(1))
        
        # 2. 匹配代码块 ``` ... ```
        match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
        if match: 
            try: return json.loads(match.group(1))
            except: pass
            
        # 3. 匹配最外层的 { ... }
        # 找到第一个 { 和最后一个 }
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            json_str = content[start:end+1]
            return json.loads(json_str)
            
        return None
    except Exception as e:
        return None

def main():
    log.header("Tinbot Core v2.2 (Robust)")

    # 1. 初始化主服务
    try:
        main_client = OpenAI(api_key=settings.API_KEY, base_url=settings.API_URL)
        state_db = StateManager()
        log.system(f"主大脑连接成功: [bold]{settings.MODEL_NAME}[/bold]")
    except Exception as e:
        log.error(f"核心服务启动失败: {e}")
        return

    # 2. 初始化视觉
    vision_engine = None
    try:
        if settings.VISION_MODEL_API_KEY:
            vision_client = OpenAI(
                api_key=settings.VISION_MODEL_API_KEY,
                base_url=settings.VISION_MODEL_URL
            )
            vision_engine = VisionEngine(vision_client, settings.VISION_MODEL_NAME)
            log.system(f"视觉引擎就绪: [bold]{settings.VISION_MODEL_NAME}[/bold]")
    except Exception:
        pass # 静默失败

    # 3. 上下文
    app_context = { "client": main_client, "vision": vision_engine, "settings": settings, "db": state_db }
    brain = SkillManager(context=app_context)

    # ================= 交互循环 =================
    while True:
        try:
            from rich.prompt import Prompt
            user_input = Prompt.ask("\n[bold cyan]🤖 指令[/bold cyan] (输入 'r' 重载)").strip()
            if not user_input: continue
            if user_input.lower() == 'r':
                brain.load_skills()
                continue
            
            # === 强化的 System Prompt ===
            sys_prompt = f"""
            你是一个能够操作电脑的 AI Agent。
            
            【可用工具】:
            {brain.get_skill_descriptions()}
            
            【回复格式】:
            你必须**严格**遵守以下 JSON 格式进行回复（不要输出任何 JSON 之外的文字）：
            
            {{
                "thought": "这里写你的思考过程（比如：用户要打开两个软件，我需要调用 computer_control...）",
                "action": "工具名",
                "args": {{ "参数名": "参数值" }}
            }}
            
            【结束任务】:
            如果任务已完成，请输出：
            {{
                "thought": "任务已完成",
                "action": "finish",
                "args": {{ "summary": "已为你打开了网易云和计算器" }}
            }}
            """
            
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_input}
            ]

            for i in range(10): 
                resp = main_client.chat.completions.create(
                    model=settings.MODEL_NAME, 
                    messages=messages
                )
                content = resp.choices[0].message.content
                messages.append({"role": "assistant", "content": content})

                # 尝试提取 JSON
                action_data = extract_json(content)
                
                # 如果提取失败，打印原始信息用于调试
                if not action_data:
                    log.think(content) # 显示原始思考
                    log.error("无法解析 JSON，正在重试...")
                    continue

                # 提取字段
                thought = action_data.get("thought", "正在执行...")
                action = action_data.get("action")
                args = action_data.get("args", {})

                # 显示思考过程
                log.think(thought)

                # 处理 Finish
                if action == "finish":
                    log.agent_response(args.get("summary", "任务完成"))
                    break
                
                # 执行工具
                if action:
                    log.action(action, args)
                    result = brain.execute(action, **args)
                    log.result(result)
                    messages.append({"role": "user", "content": f"工具输出: {result}"})
                else:
                    log.error("JSON 中缺少 'action' 字段")

        except KeyboardInterrupt:
            break
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    main()