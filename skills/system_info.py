import platform
import datetime
import os
import socket
from skills.base import Skill

class SystemInfoSkill(Skill):
    def __init__(self):
        super().__init__()
        self.name = "get_system_info"
        self.description = """
        获取当前系统的基本状态信息。
        包括：当前时间、操作系统版本、计算机名、当前用户等。
        当用户问“几点了”、“我是谁”、“这是什么电脑”时使用。
        """
        self.parameters = {
            "type": "object",
            "properties": {}, # 无需参数
            "required": []
        }

    def execute(self, **kwargs) -> str:
        try:
            # 收集信息
            info = []
            
            # 1. 时间
            now = datetime.datetime.now()
            info.append(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (Week {now.isocalendar()[1]})")
            
            # 2. 系统
            uname = platform.uname()
            info.append(f"操作系统: {uname.system} {uname.release} ({uname.machine})")
            
            # 3. 网络/主机
            hostname = socket.gethostname()
            info.append(f"主机名称: {hostname}")
            
            # 4. 用户
            # 兼容获取用户名的方式
            try:
                user = os.getlogin()
            except:
                user = os.environ.get('USERNAME') or os.environ.get('USER') or 'Unknown'
            info.append(f"当前用户: {user}")
            
            return "\n".join(info)
            
        except Exception as e:
            return f"❌ 获取信息失败: {e}"