"""
Terminal Skill (Smart)
智能终端工具 - 完美处理 cd、复合命令 (&&) 和 Windows 路径
"""

import subprocess
import os
import platform
from skills.base import Skill

# 全局变量：记忆当前路径
CURRENT_WORKING_DIR = os.getcwd()

class TerminalSkill(Skill):
    def __init__(self):
        super().__init__()
        self.name = "terminal"
        self.description = """
        通用命令行终端。
        
        【核心能力】:
        1. 文件操作: mkdir, rm, mv, cp, type/cat
        2. 路径切换: cd (支持 cd /d 跨盘符)
        3. 复合命令: 支持 &&, ||, ; 连接 (例如: cd A && python b.py)
        
        【机制说明】:
        - 纯 'cd' 命令会更新 Agent 的记忆路径。
        - 复合命令 (带 &&) 会直接在 Shell 执行，不会更新记忆路径（但操作会生效）。
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "CMD/Bash 命令"
                }
            },
            "required": ["command"]
        }

    def execute(self, command, **kwargs) -> str:
        global CURRENT_WORKING_DIR
        
        cmd = command or kwargs.get('cmd')
        if not cmd: return "❌ 错误: 空命令"
        
        # 移除首尾空白
        cmd = cmd.strip()
        print(f"💻 [Terminal] (在 {CURRENT_WORKING_DIR}) 执行: {cmd}")

        try:
            # === 智能路由逻辑 ===
            
            # 判断是否是复合命令 (含有 &&, ;, | 等)
            # 如果是复合命令，直接交给 subprocess 跑，不要尝试在 Python 层模拟 cd
            is_composite = any(op in cmd for op in ["&&", ";", "|", "||"])
            
            # 判断是否是纯 cd 命令
            is_cd = cmd.lower().startswith("cd ") and not is_composite
            
            if is_cd:
                # --- Python 层面模拟 cd (为了更新记忆) ---
                target_raw = cmd[3:].strip() # 去掉 'cd '
                
                # Windows 特殊处理: 去掉 /d 参数
                if platform.system() == "Windows" and target_raw.lower().startswith("/d"):
                    target_raw = target_raw[2:].strip()
                
                # 去掉引号
                target_raw = target_raw.strip('"').strip("'")
                
                # 计算绝对路径
                new_path = os.path.join(CURRENT_WORKING_DIR, target_raw)
                new_path = os.path.abspath(new_path)
                
                if os.path.exists(new_path) and os.path.isdir(new_path):
                    CURRENT_WORKING_DIR = new_path
                    return f"✅ 工作目录已切换至: {CURRENT_WORKING_DIR}"
                else:
                    return f"❌ 路径不存在: {new_path}"

            else:
                # --- 普通命令 或 复合命令 -> 丢给系统 Shell ---
                # 关键：cwd 参数保证了命令是在“记忆路径”下执行的
                
                # Windows 下很多命令输出是 GBK，需要解码
                encoding = 'gbk' if platform.system() == 'Windows' else 'utf-8'
                
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    cwd=CURRENT_WORKING_DIR, 
                    capture_output=True, 
                    text=True,
                    encoding=encoding,
                    errors='ignore' # 防止特殊字符报错
                )
                
                output = ""
                if result.stdout:
                    output += result.stdout
                if result.stderr:
                    output += f"\n[Error/Warning]:\n{result.stderr}"
                    
                if not output:
                    if result.returncode == 0:
                        output = "(执行成功)"
                    else:
                        output = "(执行失败，无返回内容)"

                return f"[Path: {CURRENT_WORKING_DIR}]\n$ {cmd}\n\n{output}"

        except Exception as e:
            return f"❌ 终端执行系统错误: {e}"