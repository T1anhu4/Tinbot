import sys
import os
import time
import re
import subprocess
import pyautogui
import pyperclip
import pygetwindow as gw
from openai import OpenAI
import json
import ast
from typing import Dict, Any, Callable

# ================= 配置区域 =================
API_BASE = "http://120.24.173.129:3000/api/v1"
API_KEY = "fastgpt-xEnWOUtLbvamg9kOtwtWYQpLzwNovtWLGY9WuibYKngIyYdSe2pmvUjpiM8LUTX"
MODEL_NAME = "qwen-max"

client = OpenAI(api_key=API_KEY, base_url=API_BASE)
pyautogui.FAILSAFE = True 

# ================= 工具函数 =================

def print_log(role, msg):
    colors = {
        "System": "\033[95m", "Tool": "\033[94m", "Agent": "\033[92m", 
        "Error": "\033[91m", "Think": "\033[93m", "Plan": "\033[96m", 
        "Skill": "\033[97m", "Reset": "\033[0m"
    }
    print(f"{colors.get(role, colors['Reset'])}[{role}] {msg}{colors['Reset']}")

# ================= SKILL 基类 =================

class Skill:
    """
    Skill 基类 - 所有技能都继承自这个类
    每个 Skill 必须实现:
    1. name: 技能名称
    2. description: 技能描述 (给 LLM 看的)
    3. parameters: 参数定义 (JSON Schema 格式)
    4. execute: 执行逻辑
    """
    
    def __init__(self):
        self.name = "base_skill"
        self.description = "Base skill class"
        self.parameters = {}
    
    def execute(self, **kwargs) -> str:
        """执行技能，返回结果字符串"""
        raise NotImplementedError("Subclass must implement execute()")
    
    def to_tool_definition(self) -> Dict:
        """转换为 LLM 可理解的工具定义格式"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

# ================= SKILL 1: VS Code 写代码 =================

class VSCodeWriteSkill(Skill):
    """
    Skill: VS Code 写代码
    功能: 通过 GUI 自动化将代码写入 VS Code
    """
    
    def __init__(self):
        super().__init__()
        self.name = "vscode_write"
        self.description = """
        使用 VS Code 编辑器写入代码文件。
        适用场景: 创建新的 Python 脚本、修改代码文件。
        注意: 必须提供完整的代码，不支持增量修改。
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "要创建/编辑的文件名 (如 game.py)"
                },
                "code": {
                    "type": "string",
                    "description": "完整的代码内容"
                }
            },
            "required": ["filename", "code"]
        }
    
    def _ensure_vscode_focused(self, filename: str) -> bool:
        """确保 VS Code 窗口处于激活状态"""
        subprocess.Popen(f'code "{filename}"', shell=True)
        time.sleep(2)
        
        target_window = None
        for _ in range(5):
            windows = gw.getWindowsWithTitle('Visual Studio Code')
            if windows:
                target_window = windows[0]
                break
            time.sleep(1)
        
        if not target_window:
            return False
        
        try:
            if target_window.isMinimized:
                target_window.restore()
            target_window.activate()
            time.sleep(0.5)
            return True
        except:
            return False
    
    def execute(self, code: str, filename: str = None, file: str = None) -> str:
        """执行写代码操作（支持 filename 或 file 参数）"""
        # 兼容两种参数名
        filename = filename or file
        if not filename:
            return "❌ 缺少文件名参数"
        
        print_log("Skill", f"[{self.name}] 正在写入文件: {filename}")
        
        # 1. 语法预检
        try:
            ast.parse(code)
        except SyntaxError as e:
            return f"❌ 语法错误 (Line {e.lineno}): {e.msg}"
        
        # 2. 物理文件创建
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("")
        
        # 3. VS Code 操作
        if self._ensure_vscode_focused(filename):
            # 聚焦编辑区
            pyautogui.hotkey('ctrl', '1')
            time.sleep(0.5)
            
            # 清空 + 粘贴
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.3)
            pyautogui.press('backspace')
            time.sleep(0.3)
            
            pyperclip.copy(code)
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1)
            
            # 格式化 + 保存
            pyautogui.hotkey('shift', 'alt', 'f')
            time.sleep(1)
            pyautogui.hotkey('ctrl', 's')
            time.sleep(0.5)
            
            return f"✅ 代码已写入 {filename} 并保存"
        else:
            return "❌ 无法聚焦 VS Code 窗口"

# ================= SKILL 2: 运行 Python 文件 =================

class RunPythonSkill(Skill):
    """
    Skill: 运行 Python 文件
    功能: 执行 Python 脚本，自动安装缺失的依赖库
    """
    
    def __init__(self):
        super().__init__()
        self.name = "run_python"
        self.description = """
        运行指定的 Python 文件。
        功能:
        1. 自动检测缺失的第三方库并安装
        2. 捕获运行输出和错误信息
        3. 对 GUI 程序特殊处理 (短超时)
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "要运行的 Python 文件名 (如 snake_game.py)"
                }
            },
            "required": ["filename"]
        }
        
        # 库名映射表
        self.package_mapping = {
            'cv2': 'opencv-python',
            'PIL': 'pillow',
            'docx': 'python-docx',
            'sklearn': 'scikit-learn'
        }
    
    def _install_package(self, package: str) -> bool:
        """安装 Python 包"""
        try:
            print_log("Skill", f"正在安装: {package}")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                check=True,
                capture_output=True
            )
            return True
        except:
            return False
    
    def execute(self, filename: str) -> str:
        """执行 Python 文件"""
        print_log("Skill", f"[{self.name}] 正在运行: {filename}")
        
        # 1. 文件存在性检查
        if not os.path.exists(filename):
            return f"❌ 文件不存在: {filename}"
        
        # 2. 读取代码判断是否为 GUI 程序
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        is_gui = any(keyword in content for keyword in [
            'pygame', 'tkinter', 'PyQt', 'PySide', 'wx'
        ])
        
        # 3. 运行程序
        try:
            timeout = 6 if is_gui else 30
            result = subprocess.run(
                [sys.executable, filename],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            stderr = result.stderr
            
            # 4. 处理缺失库
            if "ModuleNotFoundError" in stderr:
                match = re.search(r"No module named '(\w+)'", stderr)
                if match:
                    module_name = match.group(1)
                    # 查找真实包名
                    package = self.package_mapping.get(module_name, module_name)
                    
                    if self._install_package(package):
                        return f"✅ 已自动安装 {package}，请重新运行"
                    else:
                        return f"❌ 安装 {package} 失败"
            
            # 5. 返回运行结果
            if is_gui and result.returncode != 0:
                return f"✅ GUI 程序已启动 (测试通过)"
            
            output = f"运行结束 (退出码: {result.returncode})\n"
            if result.stdout:
                output += f"\n标准输出:\n{result.stdout}"
            if result.stderr:
                output += f"\n错误输出:\n{result.stderr}"
            
            return output
            
        except subprocess.TimeoutExpired:
            return "✅ GUI 程序已启动 (运行超时保护)" if is_gui else "❌ 运行超时"
        except Exception as e:
            return f"❌ 系统错误: {str(e)}"

# ================= SKILL 3: 列出当前目录文件 =================

class ListFilesSkill(Skill):
    """
    Skill: 列出当前目录文件
    功能: 查看当前工作目录下的所有文件
    """
    
    def __init__(self):
        super().__init__()
        self.name = "list_files"
        self.description = """
        列出当前工作目录下的所有文件和文件夹。
        适用场景: 查看有哪些文件、确认文件是否存在。
        """
        self.parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def execute(self) -> str:
        """列出当前目录文件"""
        print_log("Skill", f"[{self.name}] 正在列出当前目录文件")
        
        try:
            files = os.listdir('.')
            
            # 分类
            python_files = [f for f in files if f.endswith('.py')]
            other_files = [f for f in files if not f.endswith('.py')]
            
            result = "📂 当前目录文件列表:\n\n"
            
            if python_files:
                result += "🐍 Python 文件:\n"
                for f in python_files:
                    size = os.path.getsize(f)
                    result += f"  - {f} ({size} bytes)\n"
            
            if other_files:
                result += "\n📄 其他文件:\n"
                for f in other_files:
                    if os.path.isdir(f):
                        result += f"  - {f}/ (文件夹)\n"
                    else:
                        size = os.path.getsize(f)
                        result += f"  - {f} ({size} bytes)\n"
            
            return result if files else "当前目录为空"
            
        except Exception as e:
            return f"❌ 读取失败: {str(e)}"

# ================= SKILL 管理器 =================

class SkillManager:
    """
    Skill 管理器
    职责: 注册、查找、调用 Skills
    """
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
    
    def register(self, skill: Skill):
        """注册一个 Skill"""
        self.skills[skill.name] = skill
        print_log("System", f"✓ 已注册 Skill: {skill.name}")
    
    def get_skill(self, name: str) -> Skill:
        """获取指定 Skill"""
        return self.skills.get(name)
    
    def list_skills(self) -> list:
        """获取所有 Skill 定义 (供 LLM 调用)"""
        return [skill.to_tool_definition() for skill in self.skills.values()]
    
    def execute(self, skill_name: str, **kwargs) -> str:
        """执行指定 Skill（支持参数名自动映射）"""
        skill = self.get_skill(skill_name)
        if not skill:
            return f"❌ Skill 不存在: {skill_name}"
        
        # 参数名映射表（兼容 LLM 的常见错误）
        param_mapping = {
            'file': 'filename',  # file -> filename
            'path': 'filename',  # path -> filename
            'pkg': 'package',    # pkg -> package
        }
        
        # 自动映射参数名
        mapped_kwargs = {}
        for key, value in kwargs.items():
            mapped_key = param_mapping.get(key, key)
            mapped_kwargs[mapped_key] = value
        
        return skill.execute(**mapped_kwargs)

# ================= Agent 大脑 =================

class AgentBrain:
    def __init__(self):
        self.plan = []
        self.history = []
        self.skill_manager = SkillManager()
        
        # 注册所有 Skills
        self.skill_manager.register(VSCodeWriteSkill())
        self.skill_manager.register(RunPythonSkill())
        self.skill_manager.register(ListFilesSkill())

# ================= 规划阶段 =================

def generate_plan(brain: AgentBrain, task: str):
    """生成任务规划"""
    print_log("Think", "正在进行任务规划...")
    
    prompt = f"""
    任务目标：{task}
    
    你是一个务实的系统架构师。
    请根据任务难度进行拆解：
    1. 如果是单文件脚本，只生成 1 个步骤。
    2. 复杂任务才拆分为 2-3 步骤。
    
    直接返回 JSON 列表（无 Markdown）：
    ["Step 1: 编写完整的xxx代码", "Step 2: 运行并测试"]
    """
    
    messages = [
        {"role": "system", "content": "你是高效的 AI 架构师。"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = client.chat.completions.create(model=MODEL_NAME, messages=messages)
        content = response.choices[0].message.content
        
        # 清洗
        content = re.sub(r'```json|```', '', content).strip()
        if '[' in content and ']' in content:
            content = content[content.find('['):content.rfind(']')+1]
        
        brain.plan = json.loads(content)
        
        print_log("Plan", "任务规划:")
        for step in brain.plan:
            print(f"  [ ] {step}")
    except Exception as e:
        print_log("Error", f"规划失败: {e}")
        brain.plan = [f"Step 1: 完成 {task}"]

# ================= 执行阶段 =================

SYSTEM_PROMPT = """
你是一个 Python 全栈工程师 Agent，拥有以下技能:
{skills}

**工作规范:**
1. 必须使用 JSON 格式调用工具，不得直接输出代码
2. 每次写代码必须提供完整代码（不支持增量修改）
3. 先编写代码，再运行测试
4. **重要**: 调用工具时，参数名必须严格匹配 parameters 定义！

**JSON 格式:**
{{
    "thought": "我的思考过程...",
    "action": "skill_name",
    "args": {{"param_name": "value"}}
}}

**示例:**
调用 vscode_write 时必须用 "filename" 而不是 "file":
{{
    "action": "vscode_write",
    "args": {{"filename": "game.py", "code": "import pygame..."}}
}}
"""

def parse_agent_response(content: str) -> dict:
    """解析 Agent 回复"""
    try:
        # 策略 1: ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())
        
        # 策略 2: ``` ... ```
        match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            if json_str.startswith('{'):
                return json.loads(json_str)
        
        # 策略 3: 裸 JSON (栈匹配)
        start = content.find('{')
        if start == -1:
            return None
        
        stack = 0
        for i in range(start, len(content)):
            if content[i] == '{':
                stack += 1
            elif content[i] == '}':
                stack -= 1
                if stack == 0:
                    return json.loads(content[start:i+1])
        
        return None
    except:
        return None

def execute_plan(brain: AgentBrain, task: str):
    """执行任务"""
    # 构建 Prompt
    skills_desc = "\n".join([
        f"- {s['name']}: {s['description']}" 
        for s in brain.skill_manager.list_skills()
    ])
    
    system_prompt = SYSTEM_PROMPT.format(skills=skills_desc)
    plan_str = "\n".join(brain.plan)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"任务: {task}\n\n计划:\n{plan_str}\n\n请开始执行。"}
    ]
    
    max_turns = 15
    turn = 0
    
    while turn < max_turns:
        turn += 1
        print_log("Agent", f"执行中 (Round {turn})...")
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages
            )
        except Exception as e:
            print_log("Error", f"API 错误: {e}")
            time.sleep(3)
            continue
        
        content = response.choices[0].message.content
        messages.append({"role": "assistant", "content": content})
        
        # 解析动作
        action_data = parse_agent_response(content)
        
        if action_data:
            # 执行 Skill
            thought = action_data.get("thought", "")
            action = action_data.get("action")
            args = action_data.get("args", {})
            
            print_log("Think", thought[:100])
            print_log("Agent", f"调用 Skill -> {action}")
            
            result = brain.skill_manager.execute(action, **args)
            print_log("Tool", result[:200])
            
            messages.append({"role": "user", "content": f"[工具输出]:\n{result}"})
        else:
            # 说话
            print_log("Agent", content[:150])
            
            if "完成" in content or "成功" in content:
                print_log("System", "✅ 任务完成")
                break
            
            messages.append({
                "role": "user",
                "content": "请输出 JSON 格式的工具调用指令！"
            })
    
    if turn >= max_turns:
        print_log("Error", "达到最大轮数")

# ================= 主程序 =================

if __name__ == "__main__":
    brain = AgentBrain()
    
    # 任务设定
    user_task = "帮我写一个贪吃蛇游戏，要有分数显示，碰到墙壁游戏结束，写完后运行测试"
    
    print_log("System", f"接收任务: {user_task}")
    print_log("System", "已加载 Skills:")
    for skill_name in brain.skill_manager.skills.keys():
        print(f"  ✓ {skill_name}")
    
    print_log("System", "请双手离开键盘鼠标...")
    time.sleep(2)
    
    # 执行
    generate_plan(brain, user_task)
    execute_plan(brain, user_task)