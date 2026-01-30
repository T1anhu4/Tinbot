from typing import Dict, Any

class Skill:
    """所有技能必须继承的基类"""
    
    def __init__(self):
        self.name = "base_skill"
        self.description = "Base description"
        self.parameters = {}
        # 上下文容器：存放 VisionEngine, Client, Settings 等全局对象
        self.context: Dict[str, Any] = {} 

    def inject_context(self, context: Dict[str, Any]):
        """
        [依赖注入] 系统会自动调用此方法，把全局能力传给技能
        """
        self.context = context
        self.on_context_loaded()

    def on_context_loaded(self):
        """
        [钩子] 当上下文注入完成后调用。
        如果你的技能需要 VisionEngine，请在这里获取: self.context.get('vision')
        """
        pass
    
    def execute(self, **kwargs) -> str:
        """执行逻辑"""
        raise NotImplementedError("Subclass must implement execute()")
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """生成 Tool JSON"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }