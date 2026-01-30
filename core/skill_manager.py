import pkgutil
import inspect
import importlib
import sys
import os
from core.logger import log
from skills.base import Skill

class SkillManager:
    def __init__(self, context=None):
        self.skills = {}
        self.context = context or {}
        
        # 【核心修复】把自己注入到 context 中，允许 Skill 调用其他 Skill
        self.context['skill_manager'] = self 
        
        self.load_skills()

    def get_skill_descriptions(self):
        descs = []
        for name, skill in self.skills.items():
            params_desc = skill.parameters.get("properties", {})
            param_str = ", ".join([f"{k}: {v.get('description', '')}" for k, v in params_desc.items()])
            descs.append(f"- {name}: {skill.description.strip()} (参数: {param_str})")
        return "\n".join(descs)

    def load_skills(self):
        log.system("正在扫描插件...")
        self.skills = {}
        
        package_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'skills')
        if package_dir not in sys.path:
            sys.path.append(package_dir)

        for _, module_name, _ in pkgutil.iter_modules([package_dir]):
            if module_name == 'base': continue
            
            try:
                module = importlib.import_module(f"skills.{module_name}")
                importlib.reload(module)
                
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, Skill) and obj is not Skill:
                        instance = obj()
                        instance.inject_context(self.context)
                        self.skills[instance.name] = instance
                        log.loading(f"加载: [bold cyan]{instance.name}[/bold cyan] ({module_name}.py)")
                        
            except Exception as e:
                log.error(f"插件 {module_name} 加载失败: {e}")
                
        log.system(f"插件加载完毕，共 {len(self.skills)} 个技能。")

    def execute(self, skill_name: str, **kwargs) -> str:
        # === 智能路由表 ===
        skill_router = {
            'open_app': 'computer_control',
            'browser_nav': 'computer_control',
            'type_text': 'computer_control',
            'press_key': 'computer_control',
            'hotkey': 'computer_control',
            'mouse_click': 'computer_control',
            'scroll': 'computer_control',
            'write_code': 'vscode_write',
            'save_file': 'vscode_write',
            'cmd': 'terminal',
            'shell': 'terminal',
            'run_cmd': 'terminal',
            'visit': 'browser',
            'search': 'browser',
            'visit_dom': 'browser_dom',
            'analyze_dom': 'browser_dom'
        }

        target_skill = skill_name
        inferred_action = None
        
        if skill_name not in self.skills:
            if skill_name in skill_router:
                target_skill = skill_router[skill_name]
                inferred_action = skill_name
                print(f"[Router] 自动修正: {skill_name} -> {target_skill}")
            else:
                return f"❌ Skill不存在: {skill_name}"
        
        skill = self.skills.get(target_skill)

        # 参数映射
        clean_args = {}
        key_mapping = {
            'operation': 'action', 'cmd': 'action', 'command': 'action', 'function': 'action',
            'text': 'target', 'msg': 'target', 'message': 'target', 'url': 'target',
            'browser': 'target', 'app_name': 'target', 'app': 'target', 'Target': 'target',
            'file': 'filename', 'path': 'filename', 'file_path': 'filename', 'file_name': 'filename',
            'content': 'code'
        }

        for k, v in kwargs.items():
            new_key = key_mapping.get(k, k)
            clean_args[new_key] = v

        if inferred_action and 'action' not in clean_args:
            clean_args['action'] = inferred_action

        try:
            return skill.execute(**clean_args)
        except TypeError as e:
            return f"❌ 参数错误: {e}"
        except Exception as e:
            return f"❌ 运行时错误: {e}"