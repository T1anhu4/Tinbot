# Tinbot
A multi-skilled agent with planning and reflection capabilities, powered by Qwen-MAX.

## 📁 项目结构

```
Tinbot/
├── agent.py                    # 主程序入口
├── skills/                     # Skills 目录（模块化技能）
│   ├── __init__.py            # 包初始化文件
│   ├── base.py                # Skill 基类
│   ├── vscode_write.py        # VS Code 写代码 Skill
│   ├── run_python.py          # 运行 Python Skill
│   └── list_files.py          # 列出文件 Skill
└── README.md                   # 本文档
```

## 🎯 架构设计

### 为什么要模块化？

参考了 **MoltBot** 和 **Manus** 的设计理念：
1. ✅ **每个 Skill 是独立的文件** - 便于维护和扩展
2. ✅ **统一的基类接口** - 所有 Skill 都继承自 `Skill` 基类
3. ✅ **即插即用** - 新增 Skill 只需添加文件并注册
4. ✅ **类型安全** - 使用 JSON Schema 定义参数

---

## 🚀 快速开始

### 运行 Agent

```bash
python agent.py
```

### 自定义任务

编辑 `agent.py` 的最后几行：

```python
user_task = "你的任务描述"
```

---

## 📦 已实现的 Skills

### 1. VSCodeWriteSkill
- **文件**: `skills/vscode_write.py`
- **功能**: 通过 GUI 自动化将代码写入 VS Code
- **参数**: 
  - `filename`: 文件名
  - `code`: 完整代码

### 2. RunPythonSkill
- **文件**: `skills/run_python.py`
- **功能**: 执行 Python 文件，自动安装缺失依赖
- **参数**:
  - `filename`: 要运行的文件

### 3. ListFilesSkill
- **文件**: `skills/list_files.py`
- **功能**: 列出当前目录的所有文件
- **参数**: 无

---

## 🔧 如何添加新 Skill

### 步骤 1: 创建 Skill 文件

在 `skills/` 目录下创建 `your_skill.py`:

```python
from skills.base import Skill

class YourSkill(Skill):
    def __init__(self):
        super().__init__()
        self.name = "your_skill"
        self.description = "功能描述"
        self.parameters = {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数说明"}
            },
            "required": ["param1"]
        }
    
    def execute(self, param1: str) -> str:
        # 你的逻辑
        return "执行结果"
```

### 步骤 2: 在 `__init__.py` 中导出

编辑 `skills/__init__.py`，添加：

```python
from skills.your_skill import YourSkill

__all__ = [
    # ...
    'YourSkill',
]
```

### 步骤 3: 在主程序中注册

编辑 `agent.py` 的 `AgentBrain._register_skills()`:

```python
def _register_skills(self):
    self.skill_manager.register(VSCodeWriteSkill())
    self.skill_manager.register(RunPythonSkill())
    self.skill_manager.register(ListFilesSkill())
    self.skill_manager.register(YourSkill())  # 新增这行
```

### 步骤 4: 运行测试

```bash
python agent.py
```

Agent 会自动识别新 Skill！

---

## 🎨 与 MoltBot/Manus 的对比

| 特性 | MoltBot/Manus | 本项目 |
|------|---------------|--------|
| Skill 模块化 | ✅ TypeScript | ✅ Python |
| 独立的 Skill 文件 | ✅ | ✅ |
| 统一基类 | ✅ | ✅ |
| JSON Schema 参数定义 | ✅ | ✅ |
| 自动发现工具 | ✅ | ✅ |
| GUI 自动化 | ❌ | ✅ |

---

## 📝 Skill 开发规范

### 必须实现的属性

```python
class YourSkill(Skill):
    def __init__(self):
        self.name = "skill_name"         # 技能名称（唯一）
        self.description = "..."         # 功能描述（给 LLM 看）
        self.parameters = {...}          # JSON Schema 格式
```

### 必须实现的方法

```python
def execute(self, **kwargs) -> str:
    """
    执行逻辑
    
    Returns:
        str: 必须返回字符串结果
    """
    pass
```

### 最佳实践

1. **返回值格式化**: 使用 emoji 和清晰的文本
   ```python
   return "✅ 操作成功"
   return "❌ 操作失败: 原因"
   ```

2. **错误处理**: 捕获异常并返回友好信息
   ```python
   try:
       # ...
   except Exception as e:
       return f"❌ 错误: {str(e)}"
   ```

3. **参数兼容**: 支持常见的参数名变体
   ```python
   def execute(self, filename=None, file=None):
       filename = filename or file  # 兼容两种写法
   ```

---

## 🔮 可扩展的 Skill 示例

### 网络相关
- `WebSearchSkill`: 网络搜索
- `WebFetchSkill`: 获取网页内容
- `APICallSkill`: 调用 REST API

### 文件操作
- `ReadFileSkill`: 读取文件内容
- `EditFileSkill`: 编辑文件（支持增量修改）
- `DeleteFileSkill`: 删除文件

### 版本控制
- `GitCommitSkill`: Git 提交
- `GitPushSkill`: Git 推送
- `GitStatusSkill`: 查看 Git 状态

### AI 能力
- `ImageGenSkill`: AI 生图
- `TextToSpeechSkill`: 文字转语音
- `TranslateSkill`: 翻译

---

## 🐛 常见问题

### Q: 新增 Skill 后没生效？
A: 检查三个地方：
1. `skills/__init__.py` 是否导出
2. `agent.py` 是否注册
3. Python 缓存清理: `rm -rf skills/__pycache__`

### Q: Skill 参数名不匹配怎么办？
A: 使用 SkillManager 的自动映射功能，或在 Skill 内部做兼容处理

### Q: 如何调试 Skill？
A: 在 Skill 内部添加 `print_log()` 输出调试信息

---

## 📄 License

MIT License

---

## 🙏 致谢

- 架构设计灵感来自 [MoltBot](https://github.com/moltbot) 和 [Manus](https://github.com/manus-project)
- 感谢开源社区的贡献
```
