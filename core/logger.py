# core/logger.py
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.markdown import Markdown

# 自定义主题颜色
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "tool": "bold purple",
    "agent": "green",
    "think": "yellow italic"
})

console = Console(theme=custom_theme)

class Logger:
    @staticmethod
    def header(title):
        """打印大标题"""
        console.print(Panel(Text(title, justify="center", style="bold white"), style="blue"))

    @staticmethod
    def system(msg):
        """系统消息"""
        console.print(f"[bold blue]⚙️ SYSTEM:[/bold blue] {msg}")

    @staticmethod
    def loading(msg):
        """加载信息"""
        console.print(f"[dim]  └─ {msg}[/dim]")

    @staticmethod
    def think(content):
        """Agent思考过程 (用 Panel 包裹)"""
        # 移除可能存在的 Markdown 代码块标记，防止嵌套显示难看
        clean_content = content.replace("```json", "").replace("```", "").strip()
        if not clean_content:
            return 
            
        console.print(Panel(clean_content, title="🧠 Think", title_align="left", style="think", border_style="yellow"))

    @staticmethod
    def action(tool_name, args):
        """工具调用动作"""
        args_str = str(args)
        console.print(f"[tool]🛠️ Tool Call:[/tool] [bold]{tool_name}[/bold]")
        console.print(f"   [dim]Arguments:[/dim] {args_str}")

    @staticmethod
    def result(content):
        """工具执行结果"""
        # 如果结果太长，截断
        if len(content) > 300:
            display_content = content[:300] + "... (结果过长已截断)"
        else:
            display_content = content
        
        # 区分成功和失败
        if "❌" in content or "Error" in content:
            style = "error"
            emoji = "💥"
        else:
            style = "success"
            emoji = "✅"
            
        console.print(f"[{style}]{emoji} Result:[/ {style}] {display_content}")

    @staticmethod
    def agent_response(content):
        """Agent 的最终回复"""
        console.print(Panel(Markdown(content), title="🤖 Agent", title_align="left", style="agent", border_style="green"))

    @staticmethod
    def error(msg):
        console.print(f"[error]❌ ERROR:[/error] {msg}")

# 全局单例
log = Logger()