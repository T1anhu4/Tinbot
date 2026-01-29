"""
Skill Base Class
所有 Skill 都必须继承此基类
"""

from typing import Dict, Any


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
        """
        执行技能
        
        Args:
            **kwargs: 动态参数，由 parameters 定义
            
        Returns:
            str: 执行结果（必须是字符串）
        """
        raise NotImplementedError("Subclass must implement execute()")
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """
        转换为 LLM 可理解的工具定义格式
        
        Returns:
            dict: 包含 name, description, parameters 的字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }