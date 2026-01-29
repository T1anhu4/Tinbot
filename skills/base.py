"""
Skill Base Class
所有Skill都必须继承此基类
"""

from typing import Dict, Any


class Skill:
    """
    Skill基类 - 所有技能都继承自这个类
    
    每个Skill必须实现:
    1. name: 技能名称
    2. description: 技能描述
    3. parameters: 参数定义(JSON Schema格式)
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
            **kwargs: 动态参数，由parameters定义
            
        Returns:
            str: 执行结果（必须是字符串）
        """
        raise NotImplementedError("Subclass must implement execute()")
    
    def to_tool_definition(self) -> Dict[str, Any]:
        """
        转换为LLM可理解的工具定义格式
        
        Returns:
            dict: 包含name, description, parameters的字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }