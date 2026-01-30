"""
Computer Control Skill
OS 层级控制：打开软件、文件、窗口管理、获取已安装软件列表
"""

import pyautogui
import pyperclip
import time
import subprocess
import platform
import os
import winreg
from skills.base import Skill


class ComputerControlSkill(Skill):
    """
    电脑控制技能
    功能：打开软件、打开文件、窗口管理、文本输入、滚动等
    """
    
    def __init__(self):
        super().__init__()
        self.name = "computer_control"
        self.description = """
        操作系统控制工具。这是一个多功能工具，必须通过 'action' 参数指定具体操作。

        重要提示：
        - target 参数如果是软件名，请严格使用用户提到的原始名称（特别是中文名）。
        - 严禁将中文软件名翻译成英文（例如：不要把"网易云音乐"变成"netease-cloud-music"），否则Windows搜索无法识别！
        - 如果是打开文件（如 .xlsx, .docx），直接提供文件名即可，我会自动尝试在桌面查找。

        可用的 action (操作类型):
        1. open_app: 打开应用或文件。必须提供 target 参数（应用名或文件名）。
        2. minimize_all: 最小化所有窗口。无需 target。
        3. list_installed_apps: 列出已安装软件。无需 target。
        4. type_text: 输入文本。target 为文本内容。
        5. press_key: 按下按键。target 为键名（如 enter, esc）。
        
        【调用示例】：
        - 打开微信: {"action": "open_app", "target": "微信"}
        - 打开表格: {"action": "open_app", "target": "smaitrobot.xlsx"}
        - 列出软件: {"action": "list_installed_apps"}
        """
        self.parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "open_app", 
                        "minimize_all", 
                        "scroll", 
                        "type_text",
                        "list_installed_apps",
                        "press_key"
                    ],
                    "description": "必须填写的具体操作类型"
                },
                "target": {
                    "type": "string",
                    "description": "目标内容（应用名、文件名、文本、按键名等）"
                },
                "amount": {
                    "type": "integer",
                    "description": "滚动量（仅 scroll 时需要，负数向下）",
                    "default": -500
                }
            },
            "required": ["action"]
        }
        
        # 常用软件映射表（中文名 -> 可执行文件名）
        self.app_mapping = {
            "chrome": "chrome.exe",
            "谷歌浏览器": "chrome.exe",
            "edge": "msedge.exe",
            "浏览器": "msedge.exe",
            "vscode": "code.exe",
            "记事本": "notepad.exe",
            "计算器": "calc.exe",
            "网易云音乐": "cloudmusic.exe",
            "网易云": "cloudmusic.exe",
            "wangyiyun": "cloudmusic.exe",
            "微信": "wechat.exe",
            "qq": "qq.exe",
            "outlook": "outlook.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "ppt": "powerpnt.exe",
        }
    
    def _get_installed_apps_windows(self):
        """获取 Windows 已安装软件列表"""
        apps = []
        # 方法 1: 读取注册表
        try:
            reg_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            ]
            for reg_path in reg_paths:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey = winreg.OpenKey(key, subkey_name)
                            try:
                                app_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                if app_name and len(app_name) > 0:
                                    apps.append(app_name)
                            except:
                                pass
                            winreg.CloseKey(subkey)
                        except:
                            continue
                    winreg.CloseKey(key)
                except:
                    continue
        except Exception as e:
            print(f"注册表读取失败: {e}")
        
        # 方法 2: 读取 Start Menu
        start_menu_paths = [
            os.path.join(os.environ.get('PROGRAMDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs')
        ]
        
        for path in start_menu_paths:
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.endswith('.lnk'):
                            app_name = file.replace('.lnk', '')
                            apps.append(app_name)
        
        return sorted(list(set(apps)))

    def _get_running_processes(self):
        """获取当前运行的进程列表（返回集合用于比对）"""
        try:
            # 使用 tasklist 获取进程映像名称 /NH:无标题 /FO CSV:CSV格式
            # 使用 gbk 解码防止中文系统乱码
            output = subprocess.check_output('tasklist /NH /FO CSV', shell=True).decode('gbk', errors='ignore')
            processes = set()
            for line in output.splitlines():
                if line:
                    # 获取 "xxx.exe" 部分
                    parts = line.split(',')
                    if parts:
                        proc_name = parts[0].strip('"').lower()
                        processes.add(proc_name)
            return processes
        except:
            return set()
    
    def _open_app_windows(self, app_name: str) -> str:
        """Windows 平台打开应用（带验证机制 + 支持文件路径）"""
        
        # 1. 尝试作为文件直接打开 (os.startfile)
        # 如果包含路径符，或者有文件后缀（且不是.exe），或者在映射表之外
        is_file_likely = any(x in app_name for x in ['\\', '/', '.']) and not app_name.lower().endswith('.exe')
        
        if is_file_likely:
            try:
                target_path = app_name
                # 如果文件不存在，尝试去桌面找找
                if not os.path.exists(target_path):
                    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                    possible_path = os.path.join(desktop, app_name)
                    if os.path.exists(possible_path):
                        target_path = possible_path
                
                if os.path.exists(target_path):
                    print(f"[Debug] 正在打开文件: {target_path}")
                    os.startfile(target_path) # 相当于双击
                    time.sleep(3) # 文件打开通常较慢
                    return f"✅ 已尝试打开文件: {os.path.basename(target_path)}"
            except Exception as e:
                print(f"[Debug] 文件打开尝试失败: {e}")
                # 失败继续往下走，万一是这种名字的软件呢
        
        # 2. 准备启动软件：记录当前运行的进程快照
        print(f"[Debug] 正在启动应用 {app_name}，正在记录当前进程...")
        processes_before = self._get_running_processes()
        
        # 3. 映射表处理
        normalized_name = app_name.lower().replace(" ", "")
        target_cmd = app_name
        if normalized_name in self.app_mapping:
            target_cmd = self.app_mapping[normalized_name]
        
        print(f"[Debug] 目标指令/搜索词: {target_cmd}")

        # 4. 尝试直接运行 (subprocess)
        try:
            subprocess.Popen(target_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2) 
        except:
            pass
        
        # 5. 如果是复杂的中文名，或者上面没启动成功，尝试 Win 搜索
        # 搜索逻辑：先按 Win -> 粘贴名字 -> 回车
        print(f"[Debug] 尝试 Windows 搜索...")
        pyautogui.press('win')
        time.sleep(1)
        
        # 清空搜索框
        pyautogui.hotkey('ctrl', 'a') 
        pyautogui.press('backspace')
        
        # 确定搜索词：如果有 .exe 后缀，直接搜文件名更准；否则搜原始名称
        search_term = target_cmd if target_cmd.endswith('.exe') else app_name
        
        # 粘贴搜索词
        pyperclip.copy(search_term)
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.5) # 等待 Windows 搜索索引
        pyautogui.press('enter')
        
        # 6. 【关键步骤】验证环节
        print("[Debug] 等待软件启动 (5秒)...")
        time.sleep(5) 
        
        processes_after = self._get_running_processes()
        
        # 7. 集合运算：看看多出了什么进程
        new_processes = processes_after - processes_before
        
        # 过滤掉一些系统噪音进程
        valid_new_apps = [p for p in new_processes if p not in ['conhost.exe', 'searchapp.exe', 'tasklist.exe', 'backgroundtaskhost.exe']]
        
        if valid_new_apps:
            return f"✅ 成功检测到新进程启动: {', '.join(valid_new_apps)}"
        
        # 8. 如果没检测到新进程，检查目标进程是否本身就已经在运行了
        target_exe_slug = target_cmd.lower().replace('.exe', '')
        for p in processes_after:
            # 简单的包含匹配
            if target_exe_slug in p:
                return f"✅ 应用似乎已在运行中 (或被激活): {p}"

        return f"⚠️ 尝试打开了 '{search_term}'，但未检测到新窗口或进程启动。请确认应用名称是否正确，或尝试手动打开。"
    
    def execute(self, action: str, target: str = None, amount: int = -500, **kwargs) -> str:
        """
        执行电脑控制操作
        """
        # 容错：如果 action 为空，尝试从 kwargs 里找 'operation'
        if not action and 'operation' in kwargs:
            action = kwargs['operation']

        try:
            if action == "open_app":
                if not target:
                    return "❌ 错误：open_app 需要提供 target 参数（应用名称）"
                if isinstance(target, list):
                    results = []
                    for single_target in target:
                        if platform.system() == "Windows":
                            res = self._open_app_windows(str(single_target))
                            results.append(res)
                    return "\n".join(results)
                if platform.system() == "Windows":
                    return self._open_app_windows(target)
                else:
                    return f"❌ 暂不支持 {platform.system()} 平台"
            
            elif action == "minimize_all":
                pyautogui.hotkey('win', 'd')
                time.sleep(0.5)
                return "✅ 已最小化所有窗口"
            
            elif action == "scroll":
                pyautogui.scroll(amount)
                time.sleep(0.3)
                direction = "上" if amount > 0 else "下"
                return f"✅ 已向{direction}滚动 {abs(amount)} 像素"
            
            elif action == "type_text":
                if not target:
                    return "❌ 错误：type_text 需要提供 target 参数"
                
                pyperclip.copy(target)
                time.sleep(0.2)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.3)
                return f"✅ 已输入文本: {target[:50]}"
            
            elif action == "list_installed_apps":
                if platform.system() == "Windows":
                    apps = self._get_installed_apps_windows()
                    result = "📱 已安装的应用程序（前50个）:\n\n"
                    for i, app in enumerate(apps[:50], 1):
                        result += f"{i}. {app}\n"
                    result += f"\n总计: {len(apps)} 个应用"
                    return result
                else:
                    return f"❌ 暂不支持 {platform.system()} 平台"
            
            elif action == "press_key":
                if not target:
                    return "❌ 错误：press_key 需要提供 target 参数"
                
                pyautogui.press(target.lower())
                time.sleep(0.2)
                return f"✅ 已按下按键: {target}"
            
            else:
                return f"❌ 未知操作: {action}"
        
        except Exception as e:
            return f"❌ 执行失败: {str(e)}"