"""
Modular AI Agent with Pluggable Skills
模块化 AI Agent - 可插拔技能架构
"""

import sys
import time
import re
import json
from openai import OpenAI
from typing import Dict

# 导入所有 Skills
from skills import VSCodeWriteSkill, RunPythonSkill, ListFilesSkill

# ================= 配置区域 =================
API_BASE = "http://120.24.173.129:3000/api/v1"
API_KEY = "fastgpt-xEnWOUtLbvamg9kOtwtWYQpLzwNovtWLGY9WuibYKngIyYdSe2pmvUjpiM8LUTX"
MODEL_NAME = "qwen-max"

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

# ================= 工具函数 =================

def print_log(role, msg):
    """带颜色的日志输出"""
    colors = {
        "System": "\033[95m", "Tool": "\033[94m", "Agent": "\033[92m", 
        "Error": "\033[91m", "Think": "\033[93m", "Plan": "\033[96m", 
        "Skill": "\033[97m", "Reset": "\033[0m"
    }
    print(f"{colors.get(role, colors['Reset'])}[{role}] {msg}{colors['Reset']}")

# ================= Skill 管理器 =================

class SkillManager:
    """
    Skill 管理器
    职责: 注册、查找、调用 Skills
    """
    
    def __init__(self):
        self.skills = {}
    
    def register(self, skill):
        """注册一个 Skill"""
        self.skills[skill.name] = skill
        print_log("System", f"✓ 已注册 Skill: {skill.name}")
    
    def get_skill(self, name: str):
        """获取指定 Skill"""
        return self.skills.get(name)
    
    def list_skills(self) -> list:
        """获取所有 Skill 定义 (供 LLM 调用)"""
        return [skill.to_tool_definition() for skill in self.skills.values()]
    
    def execute(self, skill_name: str, **kwargs) -> str:
        """
        执行指定 Skill（支持参数名自动映射）
        
        Args:
            skill_name: Skill 名称
            **kwargs: 参数
            
        Returns:
            str: 执行结果
        """
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
    """Agent 核心 - 管理规划和技能"""
    
    def __init__(self):
        self.plan = []
        self.history = []
        self.skill_manager = SkillManager()
        
        # 注册所有 Skills
        self._register_skills()
    
    def _register_skills(self):
        """注册所有可用的 Skills"""
        self.skill_manager.register(VSCodeWriteSkill())
        self.skill_manager.register(RunPythonSkill())
        self.skill_manager.register(ListFilesSkill())

# ================= 规划阶段 =================

def generate_plan(brain: AgentBrain, task: str):
    """
    生成任务规划
    
    Args:
        brain: Agent 大脑
        task: 用户任务
    """
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

**任务完成标准:**
- 对于查询类任务（如"列出文件"、"查看xxx"）：调用一次工具获得结果后，直接总结并说"任务完成"
- 对于创建类任务（如"写代码"、"生成文件"）：完成创建和测试后说"任务完成"
- **禁止重复调用同一个工具**，除非上次调用失败

**JSON 格式:**
{{
    "thought": "我的思考过程...",
    "action": "skill_name",
    "args": {{"param_name": "value"}}
}}

**结束格式:**
完成任务后，直接说：
"任务完成。[简短总结]"

**示例:**
调用 vscode_write 时必须用 "filename" 而不是 "file":
{{
    "action": "vscode_write",
    "args": {{"filename": "game.py", "code": "import pygame..."}}
}}
"""

def parse_agent_response(content: str) -> dict:
    """
    解析 Agent 回复中的 JSON 指令
    
    Args:
        content: Agent 的回复内容
        
    Returns:
        dict: 解析后的 JSON 对象，失败返回 None
    """
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
    """
    执行任务规划
    
    Args:
        brain: Agent 大脑
        task: 用户任务
    """
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
    last_action = None  # 记录上一次的动作
    repeat_count = 0    # 重复计数
    
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
        
        if action_data and action_data.get("action"):
            # 执行 Skill
            thought = action_data.get("thought", "")
            action = action_data.get("action")
            args = action_data.get("args", {})
            
            print_log("Think", thought[:100] if thought else "执行中...")
            print_log("Agent", f"调用 Skill -> {action}")
            
            result = brain.skill_manager.execute(action, **args)
            
            # 检测重复调用
            if action == last_action:
                repeat_count += 1
                if repeat_count >= 2:
                    print_log("System", "⚠️ 检测到重复调用，强制终止")
                    messages.append({
                        "role": "user",
                        "content": "你已经调用过这个工具了！请总结任务结果，不要再重复调用。"
                    })
                    last_action = None
                    repeat_count = 0
                    continue
            else:
                last_action = action
                repeat_count = 0
            
            # 智能显示结果（避免刷屏，但不误导 LLM）
            if len(result) > 500:
                lines = result.split('\n')
                if len(lines) > 15:
                    preview = '\n'.join(lines[:15]) + f"\n... (共 {len(lines)} 行)"
                    print_log("Tool", preview)
                else:
                    print_log("Tool", result)
            else:
                print_log("Tool", result)
            
            messages.append({"role": "user", "content": f"[工具输出]:\n{result}"})
        else:
            # 说话
            print_log("Agent", content[:200] if len(content) > 200 else content)
            
            # 改进的任务完成检测
            finish_keywords = [
                "任务完成", "完成了", "已完成", "全部完成",
                "执行完毕", "操作完毕", "运行成功",
                "以上就是", "这就是全部", "就是这些"
            ]
            
            # 特殊情况：对于简单查询任务，如果 Agent 已经回答了问题，就结束
            is_simple_query = any(kw in task for kw in ["什么文件", "有哪些", "列出", "查看"])
            has_answered = any(kw in content for kw in ["如下", "以下", "列表", "文件夹"])
            
            should_finish = (
                any(kw in content for kw in finish_keywords) or
                (is_simple_query and has_answered and turn > 2)
            )
            
            if should_finish:
                print_log("System", "✅ 任务完成")
                break
            
            # 防止无效循环
            if turn > 5 and not action_data:
                messages.append({
                    "role": "user",
                    "content": "任务已完成，请直接说'任务完成'以结束对话。不要再输出工具调用指令。"
                })
            else:
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
    user_task = "当前目录下有什么文件"
    
    print_log("System", f"接收任务: {user_task}")
    print_log("System", "已加载 Skills:")
    for skill_name in brain.skill_manager.skills.keys():
        print(f"  ✓ {skill_name}")
    
    print_log("System", "请双手离开键盘鼠标...")
    time.sleep(2)
    
    # 执行
    generate_plan(brain, user_task)
    execute_plan(brain, user_task)