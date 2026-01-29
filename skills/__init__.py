import pkgutil
import importlib
import inspect
from .base import Skill 

def auto_discover_skills():
    """
    自动发现并实例化当前包下所有的Skill子类
    Returns:
        list: 包含所有Skill实例的列表
    """
    found_skills = []
    
    # 1. 遍历当前包路径下的所有模块
    # __path__ 指向 skills 文件夹
    for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
        
        # 2. 动态导入模块 (例如: import skills.list_files)
        full_module_name = f"{__name__}.{module_name}"
        try:
            module = importlib.import_module(full_module_name)
        except Exception as e:
            print(f"模块 {module_name} 导入失败: {e}")
            continue

        # 3. 检查模块中的类
        for name, obj in inspect.getmembers(module):
            # 必须是类 && 必须继承自Skill && 不能是Skill基类本身
            if (inspect.isclass(obj) and 
                issubclass(obj, Skill) and 
                obj is not Skill):
                
                try:
                    # 实例化技能
                    skill_instance = obj()
                    found_skills.append(skill_instance)
                except Exception as e:
                    print(f"技能 {name} 实例化失败: {e}")

    return found_skills