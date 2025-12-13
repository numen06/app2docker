# backend/database.py
"""数据库配置和会话管理"""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
import threading
import sqlite3

# 数据库文件路径
DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "app2docker.db")
DB_URL = f"sqlite:///{DB_FILE}"

# SQLite连接参数，优化并发性能
connect_args = {
    "check_same_thread": False,
    "timeout": 30.0,  # 等待锁的超时时间（秒）
}

# 创建数据库引擎
# 使用 StaticPool 和 check_same_thread=False 以支持多线程
engine = create_engine(
    DB_URL,
    connect_args=connect_args,
    poolclass=StaticPool,
    echo=False,  # 设置为 True 可以查看 SQL 语句
    pool_pre_ping=True,  # 连接前ping，检测连接是否有效
)


# 启用WAL模式以提高并发性能
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """设置SQLite的PRAGMA选项以提高并发性能"""
    cursor = dbapi_conn.cursor()
    try:
        # WAL模式：Write-Ahead Logging，提高并发读写性能
        cursor.execute("PRAGMA journal_mode=WAL")
        # 设置同步模式为NORMAL（在WAL模式下更安全）
        cursor.execute("PRAGMA synchronous=NORMAL")
        # 设置缓存大小（64MB）
        cursor.execute("PRAGMA cache_size=-65536")
        # 设置临时存储为内存
        cursor.execute("PRAGMA temp_store=MEMORY")
        # 设置忙等待超时（毫秒）
        cursor.execute("PRAGMA busy_timeout=30000")
    except Exception as e:
        print(f"⚠️ 设置SQLite PRAGMA失败: {e}")
    finally:
        cursor.close()


# 创建会话工厂
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

# 线程本地存储
_local = threading.local()


def get_db():
    """获取数据库会话（用于依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """获取数据库会话（用于直接调用）"""
    return SessionLocal()


def init_db():
    """初始化数据库（创建所有表）"""
    from backend.models import Base

    # 确保目录存在
    os.makedirs(DB_DIR, exist_ok=True)

    # 在创建表之前，先设置WAL模式（如果数据库已存在）
    if os.path.exists(DB_FILE):
        try:
            conn = sqlite3.connect(DB_FILE, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-65536")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA busy_timeout=30000")
            conn.close()
        except Exception as e:
            print(f"⚠️ 设置数据库PRAGMA失败: {e}")

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 迁移：添加webhook_allowed_branches字段（如果不存在）
    migrate_add_webhook_allowed_branches()

    print(f"✅ 数据库初始化完成: {DB_FILE}")


def migrate_add_webhook_allowed_branches():
    """迁移：为pipelines表添加webhook_allowed_branches字段"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(pipelines)")
        columns = [row[1] for row in cursor.fetchall()]

        if "webhook_allowed_branches" not in columns:
            print("🔄 添加 webhook_allowed_branches 字段到 pipelines 表...")
            # SQLite不支持直接添加JSON列，需要先添加TEXT列
            cursor.execute(
                "ALTER TABLE pipelines ADD COLUMN webhook_allowed_branches TEXT DEFAULT '[]'"
            )
            conn.commit()
            print("✅ webhook_allowed_branches 字段添加成功")
        else:
            print("✅ webhook_allowed_branches 字段已存在")

        conn.close()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ webhook_allowed_branches 字段已存在")
        else:
            print(f"⚠️ 迁移webhook_allowed_branches字段失败: {e}")
    except Exception as e:
        print(f"⚠️ 迁移webhook_allowed_branches字段失败: {e}")


def close_db():
    """关闭数据库连接"""
    SessionLocal.remove()
