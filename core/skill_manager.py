import os
import pkgutil
import importlib
import inspect
import sys
from skills.base import Skill
from core.logger import log

class SkillManager:
    def __init__(self, context: dict = None):
        self.skills = {}
        self.context = context or {} # 全局上下文
        self.skills_package_path = "skills" # 插件包名
        
        # 初始化时加载
        self.load_skills()

    def load_skills(self):
        """扫描并加载所有插件 (支持热重载)"""
        log.system("正在扫描插件...")
        self.skills = {}
        
        # 1. 获取 skills 文件夹的物理路径
        # 假设当前运行目录是项目根目录
        package_dir = os.path.join(os.getcwd(), self.skills_package_path)
        
        if not os.path.exists(package_dir):
            os.makedirs(package_dir)

        # 2. 遍历模块
        for _, module_name, _ in pkgutil.iter_modules([package_dir]):
            if module_name == "base": continue # 跳过基类文件
            
            full_module_name = f"{self.skills_package_path}.{module_name}"
            
            try:
                # 3. 动态导入/重载
                if full_module_name in sys.modules:
                    module = importlib.reload(sys.modules[full_module_name])
                else:
                    module = importlib.import_module(full_module_name)
                
                # 4. 查找并实例化 Skill 子类
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, Skill) and obj is not Skill:
                        instance = obj()
                        
                        # [关键步骤] 依赖注入：把 Vision 塞给它
                        instance.inject_context(self.context)
                        
                        self.skills[instance.name] = instance
                        log.loading(f"加载: [bold]{instance.name}[/bold]")
                        
            except Exception as e:
                log.system(f"  加载失败 {module_name}: {e}")
        
        log.system(f"插件加载完毕，共 {len(self.skills)} 个技能。")

    def get_skill_descriptions(self):
        return "\n".join([f"- {s.name}: {s.description[:80]}..." for s in self.skills.values()])

    def execute(self, skill_name: str, **kwargs) -> str:
        skill = self.skills.get(skill_name)
        if not skill:
            return f"Skill不存在: {skill_name}"
        
        # [参数自适应] 你的容错逻辑放在这里，所有插件共享
        param_mapping = {
            'file': 'filename', 'path': 'filename',
            'operation': 'action', 'cmd': 'action',
            'content': 'target', 'text': 'target'
        }
        
        clean_args = {}
        for k, v in kwargs.items():
            clean_args[param_mapping.get(k, k)] = v
            
        try:
            return skill.execute(**clean_args)
        except TypeError as e:
            return f"参数错误: {e}"
        except Exception as e:
            return f"运行时错误: {e}"