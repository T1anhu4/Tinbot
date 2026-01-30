import time
import re
import json
import traceback
import platform
from openai import OpenAI
from core.config import settings
from core.skill_manager import SkillManager
from core.vision import VisionEngine
from core.state import StateManager
from core.logger import log, console 

def extract_json(content):
    """JSON 提取器"""
    if not content: return None
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(content):
        brace_pos = content.find('{', pos)
        if brace_pos == -1: break
        try:
            obj, end_pos = decoder.raw_decode(content, idx=brace_pos)
            return obj 
        except json.JSONDecodeError:
            pos = brace_pos + 1
            continue
    return None

def clean_history_images(history):
    """
    清理历史记录中的图片，只保留最新的一张。
    旧的图片会变成 "(Image omitted)" 占位符，保留上下文但丢弃Token负载。
    """
    # 从后往前遍历，保留遇到的第一张图（也就是最新的图）
    kept_one = False
    
    # 倒序遍历
    for i in range(len(history) - 1, -1, -1):
        msg = history[i]
        if isinstance(msg.get("content"), list): # 多模态消息
            new_content = []
            for item in msg["content"]:
                if item.get("type") == "image_url":
                    if not kept_one:
                        # 是最新的图，保留
                        new_content.append(item)
                        kept_one = True
                    else:
                        # 已经保留过一张了，剩下的旧图全部删掉！
                        new_content.append({"type": "text", "text": "[历史截图已移除以节省Token]"})
                else:
                    new_content.append(item)
            msg["content"] = new_content

def main():
    log.header("Tinbot Core v2.9 (Vision Loop)")

    # 1. 初始化
    try:
        main_client = OpenAI(
            api_key=settings.API_KEY, 
            base_url=settings.API_URL,
            timeout=300.0,
            max_retries=2 
        )
        state_db = StateManager()
        log.system(f"主大脑: [bold]{settings.MODEL_NAME}[/bold]")
    except Exception as e:
        log.error(f"启动失败: {e}")
        return

    # 2. 视觉初始化
    vision_engine = None
    try:
        if settings.VISION_MODEL_API_KEY:
            vision_client = OpenAI(
                api_key=settings.VISION_MODEL_API_KEY,
                base_url=settings.VISION_MODEL_URL,
                timeout=60.0 
            )
            vision_engine = VisionEngine(vision_client, settings.VISION_MODEL_NAME)
            log.system(f"视觉引擎: [bold]{settings.VISION_MODEL_NAME}[/bold] (已激活)")
        else:
            log.system("视觉引擎: 未配置 (盲人模式)")
    except: pass 

    # 3. 上下文
    app_context = { "client": main_client, "vision": vision_engine, "settings": settings, "db": state_db }
    brain = SkillManager(context=app_context)
    current_os = platform.system()

    # 4. Prompt
    executor_sys_prompt_template = """
    你是一个全能 AI Agent。
    【运行环境】: {current_os}
    
    【能力】:
    1. 你可以执行终端命令 (terminal)。
    2. 你可以操作电脑 GUI (computer_control)。
    3. 【关键】：你拥有视觉能力。每当你执行 GUI 操作后，系统会自动截图并告诉你屏幕上发生了什么。请根据视觉反馈来判断下一步。
    
    【工具列表】:
    {tools}
    
    【回复格式】:
    必须输出标准 JSON: {{"thought": "...", "action": "工具名", "args": {{...}}}}
    
    【结束规则】:
    任务完成请调用: {{"action": "finish", "args": {{"summary": "..."}}}}
    """

    current_tools_desc = brain.get_skill_descriptions()
    formatted_prompt = executor_sys_prompt_template.format(tools=current_tools_desc, current_os=current_os)
    chat_history = [{"role": "system", "content": formatted_prompt}]

    while True:
        try:
            from rich.prompt import Prompt
            user_input = Prompt.ask("\n[bold cyan]->> 指令[/bold cyan] (输入 'r' 重载, 'c' 清空)").strip()
            
            if not user_input: continue
            
            if user_input.lower() == 'r':
                brain.load_skills()
                current_tools_desc = brain.get_skill_descriptions()
                chat_history[0]["content"] = executor_sys_prompt_template.format(tools=current_tools_desc, current_os=current_os)
                log.system("插件已重载")
                continue
            if user_input.lower() == 'c':
                chat_history = [{"role": "system", "content": executor_sys_prompt_template.format(tools=current_tools_desc, current_os=current_os)}]
                log.system("记忆已清空")
                continue
            
            # Planner
            with console.status("[bold yellow]📋 正在规划...[/bold yellow]", spinner="star"):
                try:
                    planner_prompt = f"""
                    你是一个自动化 Agent 的任务架构师。
                    你拥有以下工具箱：
                    {current_tools_desc}
                    
                    【任务】: {user_input}
                    【环境】: {current_os}
                    
                    【规划策略】:
                    1. 浏览网页是动态的：先 visit 访问，然后根据视觉反馈决定是 scroll (滚动) 还是 click (点击)。
                    2. 不要试图一次性把所有步骤写死。
                    3. 示例计划：
                       - Step 1: 使用 browser visit 访问 github.com/xxx。
                       - Step 2: 观察屏幕，如果是 Bilibili，寻找视频列表。
                    """
                    
                    plan_resp = main_client.chat.completions.create(
                        model=settings.MODEL_NAME, 
                        messages=[{"role": "system", "content": "你是个任务规划师。"}, {"role": "user", "content": planner_prompt}]
                    )
                    plan_content = plan_resp.choices[0].message.content
                    log.plan(plan_content)
                    chat_history.append({"role": "user", "content": f"任务: {user_input}\n\n计划:\n{plan_content}\n\n请执行。"})
                except Exception as e:
                    log.error(f"规划失败: {e}")
                    continue

            # Executor Loop
            for i in range(15): 
                with console.status(f"[bold green] 思考中 (Step {i+1})...[/bold green]", spinner="dots"):
                    try:
                        resp = main_client.chat.completions.create(model=settings.MODEL_NAME, messages=chat_history)
                        content = resp.choices[0].message.content
                    except Exception as e:
                        log.error(f"模型响应错误: {e}")
                        break

                if not content: break
                chat_history.append({"role": "assistant", "content": content})
                action_data = extract_json(content)
                
                if not action_data:
                    if len(content.strip()) > 0: log.agent_response(content) 
                    break 

                thought = action_data.get("thought", "")
                action = action_data.get("action")
                args = action_data.get("args", {})

                if thought: log.think(thought)

                if action == "finish" or action == "任务完成":
                    log.agent_response(args.get("summary", "任务完成"))
                    break
                
                if action:
                    log.action(action, args)
                    
                    # 1. 执行工具
                    with console.status(f"[bold blue] 执行 {action}...[/bold blue]", spinner="earth"):
                        result = brain.execute(action, **args)
                    log.result(result)
                    
                    # === 2. 视觉闭环 (Vision Loop) ===
                    # 只有执行了 GUI 相关的工具，才需要看屏幕
                    # 如果只是 ls, cd, get_time，没必要浪费钱和时间去截图
                    gui_tools = ["computer_control", "vscode_write", "email_visual", "browser_use"]
                    
                    vision_feedback = ""
                    if vision_engine and action in gui_tools:
                        with console.status("[bold purple] 正在观察屏幕...[/bold purple]", spinner="point"):
                            # 稍微等一下 UI 渲染 (比如窗口弹出动画)
                            time.sleep(2.0)
                            # 让视觉模型验证刚才的操作
                            observation = vision_engine.verify_action(action, str(args))
                            vision_feedback = f"\n\n[ 视觉观察反馈]: {observation}"
                            
                            # 打印出来让你看到
                            console.print(f"[bold purple] 视觉反馈:[/bold purple] {observation}")

                    # 3. 将工具结果 + 视觉反馈 存入记忆
                    full_feedback = f"工具输出: {result}{vision_feedback}"
                    chat_history.append({"role": "user", "content": full_feedback})
                    
                    clean_history_images(chat_history)
                else:
                    break
            
            if len(chat_history) > 20:
                chat_history = [chat_history[0]] + chat_history[-10:]

        except KeyboardInterrupt:
            break
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    main()