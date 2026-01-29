import sqlite3
import json
import os

class StateManager:
    def __init__(self, db_path=r"./memory/state.db"):
        self.db_path = db_path
        
        # 自动创建目录（防止因为目录不存在报错）
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 初始化数据库表
        self._init_db()
        
    def _init_db(self):
        """初始化数据库结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建表（包含 task_content）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                task_content TEXT,            -- 存任务目标
                plan TEXT,                    -- 存 Plan JSON
                history TEXT,                 -- 存 History JSON
                current_step INTEGER,
                status TEXT,                  -- running 或 done
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def list_running_sessions(self):
        """列出所有未完成的任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, task_content, current_step FROM sessions WHERE status='running'")
        rows = cursor.fetchall()
        conn.close()
        return rows 

    def save_session(self, session_id, task_content, brain, status="running"):
        """
        [核心修复] 保存会话
        增加了 task_content 参数，并适配了新的 SQL 结构
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 序列化数据
        plan_json = json.dumps(brain.plan, ensure_ascii=False)
        history_json = json.dumps(brain.history, ensure_ascii=False)

        cursor.execute('''
            INSERT OR REPLACE INTO sessions 
            (session_id, task_content, plan, history, current_step, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session_id, 
            task_content,     # 必填：任务内容
            plan_json, 
            history_json,
            brain.current_step,
            status
        ))
        conn.commit()
        conn.close()
        # print(f"💾 状态已保存 (Step {brain.current_step})")

    def load_session(self, session_id):
        """
        [核心修复] 读取会话
        现在返回的数据结构里包含了 status 和 task_content
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT plan, history, current_step, status, task_content FROM sessions WHERE session_id=?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "plan": json.loads(row[0]),
                "history": json.loads(row[1]),
                "current_step": row[2],
                "status": row[3],
                "task_content": row[4]
            }
        return None