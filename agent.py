import sys
import os
import time
import re
import subprocess
import random
import pyautogui  # 新增：用于控制键盘鼠标
import pyperclip
from openai import OpenAI

# ================= 配置区域 =================
API_BASE = "http://120.24.173.129:3000/api/v1"
API_KEY = "fastgpt-v43vbGD5I0PdHpYSweJrwn7NcjKom7W8xBvGQTjg5lmkcV7PcnMcZeh8KaRUX"
MODEL_NAME = "qwen-max"

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

# PyAutoGUI 安全设置：如果鼠标移动到屏幕左上角，强制停止脚本 (防止失控)
pyautogui.FAILSAFE = True 

# ================= 1. 视觉与GUI工具 (手) =================

def open_vscode_and_type(filename, code_content):
    """
    【最终稳定版】
    策略：
    1. 换行后，VS Code 会自动送缩进（空格）。
    2. 我们不删这些空格（因为容易误删换行符）。
    3. 我们按两次 Home 回到行首，直接粘贴新代码。
    4. 此时行尾会有多余的空格，但这不影响代码运行。
    5. 最后统一用格式化快捷键清理现场。
    """
    print_system_msg(f"正在打开 VS Code 并创建文件: {filename} ...")
    
    # 1. 打开文件
    subprocess.Popen(f'code "{filename}"', shell=True)
    time.sleep(3) # 给足启动时间

    # 2. 聚焦并清空
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.press('backspace')
    
    print_system_msg("开始输入代码...")
    
    lines = code_content.split('\n')
    
    for i, line in enumerate(lines):
        # 即使是空行，我们也处理，保证格式统一
        
        # 1. 复制当前行
        if line:
            pyperclip.copy(line)
        
        # 2. 粘贴 (如果有内容)
        if line:
            pyautogui.hotkey('ctrl', 'v')
        
        time.sleep(0.05) 
        
        # 3. 换行准备进入下一行
        if i < len(lines) - 1:
            pyautogui.press('enter')
            time.sleep(0.1) # 等待换行
            
            # === 核心修改 ===
            # 不要按 Backspace 删除缩进了！
            # 只要强行回到最左边即可。
            # VS Code 按一次 Home 可能只回到缩进处，按两次一定回到行首。
            pyautogui.press(['home', 'home']) 
            
            # 现在光标在第0列，下一行粘贴时会自带缩进。
            # 原本 VS Code 自动生成的缩进现在变成了行尾的空格，
            # Python 解释器会忽略行尾空格，所以这是安全的。
            # =================
            
        # 随机延时，增加拟人感
        time.sleep(random.uniform(0.05, 0.15))

    # 4. 最后的大扫除：格式化代码
    # 这会把我们留下的行尾垃圾空格全部自动清理掉
    print_system_msg("输入完成，正在整理格式...")
    time.sleep(1)
    pyautogui.hotkey('shift', 'alt', 'f')
    time.sleep(1)

    # 5. 保存
    pyautogui.hotkey('ctrl', 's')
    print_system_msg("文件已保存。")
    time.sleep(1)

def print_system_msg(msg):
    print(f"\033[92m[Agent Action] {msg}\033[0m")

# ================= 2. 执行工具 (验证) =================

def run_python_file(filename):
    """
    运行代码，具备【智能依赖检测】与【环境自动净化】能力
    """
    print_system_msg(f"正在终端运行 {filename} 验证结果...")
    
    max_install_attempts = 3
    attempt = 0
    
    # 禁止自动安装的名单
    DENY_LIST = {'exceptions', 'sys', 'os', 're', 'time', 'json', 'math', 'random', 'subprocess'}
    
    while attempt < max_install_attempts:
        attempt += 1
        
        try:
            result = subprocess.run(
                [sys.executable, filename], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            stdout = result.stdout
            stderr = result.stderr
            output_msg = ""
            if stdout: output_msg += f"输出:\n{stdout}\n"
            if stderr: output_msg += f"报错:\n{stderr}\n"
            
            # === 核心升级 ===
            if "ModuleNotFoundError" in stderr:
                match = re.search(r"No module named '(\w+)'", stderr)
                if match:
                    missing_module = match.group(1)
                    
                    # 1. 检查黑名单
                    if missing_module in DENY_LIST:
                        # 【特例】检测是否是 docx 库导致的 Python 2/3 兼容性问题
                        # 现象：报错缺 exceptions，且报错文件路径包含 docx.py
                        if missing_module == 'exceptions' and ('docx.py' in stderr or 'docx\\' in stderr or 'docx/' in stderr):
                             print_system_msg("环境诊断：检测到安装了错误的 'docx' 库（Python 2 旧版）。")
                             print_system_msg("正在自动卸载 'docx' 并安装正确的 'python-docx'...")
                             
                             # 自动清理环境
                             subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "docx"], capture_output=True)
                             subprocess.run([sys.executable, "-m", "pip", "install", "python-docx"], check=True)
                             
                             print_system_msg("修复完成，正在重试运行...")
                             continue # 立即重试，不要把错误抛给 LLM
                        
                        return result.returncode, f"代码错误：试图导入不存在或已移除的模块 '{missing_module}' (可能是 Python 2/3 兼容性问题)，请重写代码。\n{output_msg}"

                    # 2. 智能映射表
                    install_name = missing_module
                    install_map = {
                        'cv2': 'opencv-python',
                        'PIL': 'pillow',
                        'sklearn': 'scikit-learn',
                        'docx': 'python-docx', # 代码里 import docx，实际装 python-docx
                        'yaml': 'pyyaml',
                        'bs4': 'beautifulsoup4'
                    }
                    
                    if missing_module in install_map:
                        install_name = install_map[missing_module]
                        
                    print_system_msg(f"检测到缺失库: {missing_module} (安装名: {install_name})，正在自动安装...")
                    subprocess.run([sys.executable, "-m", "pip", "install", install_name], check=True)
                    print_system_msg(f"库 {install_name} 安装完成，准备重试运行...")
                    continue 
            
            if not output_msg: output_msg = "程序运行成功，无输出。"
            return result.returncode, output_msg

        except Exception as e:
            return -1, f"系统执行错误: {str(e)}"
            
    return -1, f"多次自动修复失败，最终报错:\n{output_msg}"

# ================= 3. 大脑与逻辑处理 =================

def extract_code(llm_response):
    """从 Markdown 块中提取代码和文件名"""
    # 尝试提取文件名
    filename_match = re.search(r'#\s*filename:\s*(\w+\.py)', llm_response)
    filename = filename_match.group(1) if filename_match else "generated_task.py"
    
    # 尝试提取代码块
    code_match = re.search(r'```python(.*?)```', llm_response, re.DOTALL)
    if code_match:
        code = code_match.group(1).strip()
    else:
        # 如果没有 markdown 标记，假设全文是代码（不太安全，但作为兜底）
        code = llm_response.replace(filename_match.group(0), "") if filename_match else llm_response

    return filename, code

def agent_loop(task_description):
    """Agent 主循环"""
    
    history = [
        {"role": "system", "content": """
你是一个高级 Python 自动化 Agent。
你的目标是编写代码解决用户的问题。
每次输出必须包含：
1. 第一行注释写明文件名，格式：`# filename: xxx.py`
2. Python 代码块。

如果代码报错，你需要分析错误原因，并重新输出完整的修正后的代码。
不要只输出修改的部分，要输出整个文件的代码。
"""},
        {"role": "user", "content": task_description}
    ]

    max_retries = 3 # 最大自动纠错次数
    retry_count = 0

    while retry_count < max_retries:
        print_system_msg("思考中...")
        
        # 1. 调用 LLM
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=history,
            temperature=0.7
        )
        content = response.choices[0].message.content
        print(f"\033[90m[LLM Thought]\n{content}\033[0m\n")

        # 2. 解析代码
        filename, code = extract_code(content)
        
        if not code:
            print_system_msg("LLM 未返回有效代码，重试...")
            history.append({"role": "assistant", "content": content})
            history.append({"role": "user", "content": "请提供有效的 Python 代码块。"})
            continue

        # 3. 视觉动作：打开 VS Code 并敲代码
        open_vscode_and_type(filename, code)

        # 4. 运行验证
        return_code, output = run_python_file(filename)
        print(f"--- 运行结果 ---\n{output}")

        if return_code == 0 and "Error" not in output and "Traceback" not in output:
            print_system_msg("任务完成！代码运行成功。")
            break
        else:
            print_system_msg(f"检测到错误，准备进行第 {retry_count+1} 次自我修复...")
            retry_count += 1
            
            # 将错误信息喂回给 LLM
            history.append({"role": "assistant", "content": content})
            error_feedback = f"代码运行报错了，请修复。报错信息如下：\n{output}\n请重新输出完整的修复后的代码。"
            history.append({"role": "user", "content": error_feedback})
            
    if retry_count >= max_retries:
        print_system_msg("达到最大重试次数，任务失败。")

# ================= 入口 =================

if __name__ == "__main__":
    # 示例任务：你可以改成任何你想要的
    user_task = "在本目录下写一个python脚本，写一份工作每周汇报word文档然后保存到本地下，我是干人事和财务的，你随便编，最后打印'Done'。"
    
    print_system_msg(f"接收任务: {user_task}")
    print_system_msg("请注意：接下来的几秒钟不要移动鼠标！")
    time.sleep(3) # 给用户一点反应时间
    
    agent_loop(user_task)