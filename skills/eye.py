# skills/eye.py
from skills.base import Skill

class EyeSkill(Skill):
    def __init__(self):
        super().__init__()
        self.name = "look" # 技能名叫 look
        self.description = "主动看一眼当前屏幕。用于读取屏幕文字、确认状态或寻找报错信息。"
        self.parameters = {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "你想知道什么？(例如: '计算器显示的结果是多少')"
                }
            },
            "required": ["question"]
        }

    def execute(self, question, **kwargs) -> str:
        vision = self.context.get("vision")
        if not vision: return "❌ 视觉引擎未就绪"
        print(f"👀 [Skill] 正在主动观察: {question}")
        return vision.see_and_think(question)