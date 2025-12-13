# backend/migrate_export_tasks.py
"""迁移 export_tasks 表结构"""
import sqlite3
import os

DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "app2docker.db")

def migrate_export_tasks():
    """迁移 export_tasks 表结构"""
    if not os.path.exists(DB_FILE):
        print("数据库文件不存在，无需迁移")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='export_tasks'")
        if not cursor.fetchone():
            print("export_tasks 表不存在，将在下次初始化时创建")
            conn.close()
            return
        
        # 检查是否已有新字段
        cursor.execute("PRAGMA table_info(export_tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'image' in columns:
            print("export_tasks 表结构已是最新，无需迁移")
            conn.close()
            return
        
        print("开始迁移 export_tasks 表...")
        
        # 创建新表
        cursor.execute("""
            CREATE TABLE export_tasks_new (
                task_id VARCHAR(36) PRIMARY KEY,
                task_type VARCHAR(50) DEFAULT 'export',
                image VARCHAR(255),
                tag VARCHAR(255) DEFAULT 'latest',
                compress VARCHAR(50) DEFAULT 'none',
                registry VARCHAR(255),
                use_local BOOLEAN DEFAULT 0,
                status VARCHAR(50) DEFAULT 'pending',
                file_path VARCHAR(512),
                file_size INTEGER,
                source VARCHAR(50) DEFAULT '手动导出',
                created_at DATETIME,
                completed_at DATETIME,
                error TEXT
            )
        """)
        
        # 如果有旧数据，尝试迁移（旧表结构不同，可能无法迁移）
        cursor.execute("SELECT COUNT(*) FROM export_tasks")
        old_count = cursor.fetchone()[0]
        if old_count > 0:
            print(f"⚠️ 发现 {old_count} 条旧数据，由于表结构变化较大，将清空旧数据")
        
        # 删除旧表
        cursor.execute("DROP TABLE export_tasks")
        
        # 重命名新表
        cursor.execute("ALTER TABLE export_tasks_new RENAME TO export_tasks")
        
        # 创建索引
        cursor.execute("CREATE INDEX idx_export_task_status ON export_tasks(status)")
        cursor.execute("CREATE INDEX idx_export_task_created ON export_tasks(created_at)")
        
        conn.commit()
        print("✅ export_tasks 表迁移完成")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_export_tasks()

