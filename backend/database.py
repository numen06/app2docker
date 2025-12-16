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
    
    # 迁移：添加Portainer相关字段到agent_hosts表（如果不存在）
    migrate_add_portainer_fields()
    
    # 迁移：修改token字段允许NULL（如果表已存在且token字段不允许NULL）
    migrate_token_nullable()
    
    # 迁移：修复JSON字段的无效数据
    migrate_fix_json_fields()
    
    # 迁移：添加started_at字段到tasks表（如果不存在）
    migrate_add_started_at_field()

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


def migrate_add_portainer_fields():
    """迁移：为agent_hosts表添加Portainer相关字段"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_hosts'")
        if not cursor.fetchone():
            conn.close()
            return

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(agent_hosts)")
        columns = [row[1] for row in cursor.fetchall()]

        # 添加 host_type 字段
        if "host_type" not in columns:
            print("🔄 添加 host_type 字段到 agent_hosts 表...")
            cursor.execute(
                "ALTER TABLE agent_hosts ADD COLUMN host_type VARCHAR(20) DEFAULT 'agent'"
            )
            conn.commit()
            print("✅ host_type 字段添加成功")
        
        # 添加 portainer_url 字段
        if "portainer_url" not in columns:
            print("🔄 添加 portainer_url 字段到 agent_hosts 表...")
            cursor.execute(
                "ALTER TABLE agent_hosts ADD COLUMN portainer_url VARCHAR(512)"
            )
            conn.commit()
            print("✅ portainer_url 字段添加成功")
        
        # 添加 portainer_api_key 字段
        if "portainer_api_key" not in columns:
            print("🔄 添加 portainer_api_key 字段到 agent_hosts 表...")
            cursor.execute(
                "ALTER TABLE agent_hosts ADD COLUMN portainer_api_key TEXT"
            )
            conn.commit()
            print("✅ portainer_api_key 字段添加成功")
        
        # 添加 portainer_endpoint_id 字段
        if "portainer_endpoint_id" not in columns:
            print("🔄 添加 portainer_endpoint_id 字段到 agent_hosts 表...")
            cursor.execute(
                "ALTER TABLE agent_hosts ADD COLUMN portainer_endpoint_id INTEGER"
            )
            conn.commit()
            print("✅ portainer_endpoint_id 字段添加成功")

        conn.close()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ Portainer 相关字段已存在")
        else:
            print(f"⚠️ 迁移Portainer字段失败: {e}")
    except Exception as e:
        print(f"⚠️ 迁移Portainer字段失败: {e}")


def migrate_token_nullable():
    """迁移：修改agent_hosts表的token字段允许NULL"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_hosts'")
        if not cursor.fetchone():
            conn.close()
            return

        # 检查token字段的定义
        cursor.execute("PRAGMA table_info(agent_hosts)")
        columns = cursor.fetchall()
        
        token_column = None
        for col in columns:
            if col[1] == 'token':  # col[1] 是列名
                token_column = col
                break
        
        if token_column:
            # col[3] 是 notnull 标志（1表示NOT NULL，0表示允许NULL）
            if token_column[3] == 1:
                print("🔄 修改 token 字段允许 NULL...")
                # SQLite不支持直接修改列约束，需要重建表
                # 1. 创建新表
                cursor.execute("""
                    CREATE TABLE agent_hosts_new (
                        host_id VARCHAR(36) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL UNIQUE,
                        host_type VARCHAR(20) DEFAULT 'agent',
                        token VARCHAR(64) UNIQUE,
                        portainer_url VARCHAR(512),
                        portainer_api_key TEXT,
                        portainer_endpoint_id INTEGER,
                        status VARCHAR(20) DEFAULT 'offline',
                        last_heartbeat DATETIME,
                        host_info TEXT DEFAULT '{}',
                        docker_info TEXT DEFAULT '{}',
                        description TEXT DEFAULT '',
                        created_at DATETIME,
                        updated_at DATETIME
                    )
                """)
                
                # 2. 复制数据（明确指定列顺序，确保 JSON 字段正确）
                cursor.execute("""
                    INSERT INTO agent_hosts_new (
                        host_id, name, host_type, token, portainer_url, portainer_api_key, 
                        portainer_endpoint_id, status, last_heartbeat, host_info, docker_info, 
                        description, created_at, updated_at
                    )
                    SELECT 
                        host_id, name, 
                        COALESCE(host_type, 'agent') as host_type,
                        token, portainer_url, portainer_api_key, portainer_endpoint_id,
                        COALESCE(status, 'offline') as status,
                        last_heartbeat,
                        CASE 
                            WHEN typeof(host_info) = 'text' AND host_info IS NOT NULL 
                            THEN host_info 
                            ELSE '{}' 
                        END as host_info,
                        CASE 
                            WHEN typeof(docker_info) = 'text' AND docker_info IS NOT NULL 
                            THEN docker_info 
                            ELSE '{}' 
                        END as docker_info,
                        COALESCE(description, '') as description,
                        created_at, updated_at
                    FROM agent_hosts
                """)
                
                # 3. 删除旧表
                cursor.execute("DROP TABLE agent_hosts")
                
                # 4. 重命名新表
                cursor.execute("ALTER TABLE agent_hosts_new RENAME TO agent_hosts")
                
                # 5. 重新创建索引
                cursor.execute("CREATE UNIQUE INDEX idx_agent_host_token ON agent_hosts(token)")
                cursor.execute("CREATE INDEX idx_agent_host_status ON agent_hosts(status)")
                cursor.execute("CREATE INDEX idx_agent_host_name ON agent_hosts(name)")
                cursor.execute("CREATE INDEX idx_agent_host_type ON agent_hosts(host_type)")
                
                conn.commit()
                print("✅ token 字段已修改为允许 NULL")
            else:
                print("✅ token 字段已允许 NULL")
        else:
            print("⚠️ 未找到 token 字段")

        conn.close()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            print("✅ agent_hosts 表不存在，无需迁移")
        else:
            print(f"⚠️ 迁移token字段失败: {e}")
    except Exception as e:
        print(f"⚠️ 迁移token字段失败: {e}")


def migrate_add_started_at_field():
    """迁移：为tasks表添加started_at字段"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]

        if "started_at" not in columns:
            print("🔄 添加 started_at 字段到 tasks 表...")
            cursor.execute(
                "ALTER TABLE tasks ADD COLUMN started_at DATETIME"
            )
            conn.commit()
            print("✅ started_at 字段添加成功")
        else:
            print("✅ started_at 字段已存在")

        conn.close()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ started_at 字段已存在")
        else:
            print(f"⚠️ 迁移started_at字段失败: {e}")
    except Exception as e:
        print(f"⚠️ 迁移started_at字段失败: {e}")


def migrate_fix_json_fields():
    """迁移：修复agent_hosts表中host_info和docker_info字段的无效JSON数据"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_hosts'")
        if not cursor.fetchone():
            conn.close()
            return

        # 获取所有记录
        cursor.execute("SELECT host_id, host_info, docker_info FROM agent_hosts")
        rows = cursor.fetchall()
        
        fixed_count = 0
        for row in rows:
            host_id, host_info, docker_info = row
            
            # 修复 host_info
            host_info_fixed = None
            try:
                if host_info:
                    # 尝试解析 JSON
                    import json
                    json.loads(host_info)
                    host_info_fixed = host_info
                else:
                    host_info_fixed = '{}'
            except (json.JSONDecodeError, TypeError):
                # 如果不是有效的 JSON，重置为空对象
                host_info_fixed = '{}'
                fixed_count += 1
            
            # 修复 docker_info
            docker_info_fixed = None
            try:
                if docker_info:
                    # 尝试解析 JSON
                    import json
                    json.loads(docker_info)
                    docker_info_fixed = docker_info
                else:
                    docker_info_fixed = '{}'
            except (json.JSONDecodeError, TypeError):
                # 如果不是有效的 JSON，重置为空对象
                docker_info_fixed = '{}'
                fixed_count += 1
            
            # 如果数据需要修复，更新记录
            if host_info_fixed != host_info or docker_info_fixed != docker_info:
                cursor.execute("""
                    UPDATE agent_hosts 
                    SET host_info = ?, docker_info = ?
                    WHERE host_id = ?
                """, (host_info_fixed, docker_info_fixed, host_id))
        
        if fixed_count > 0:
            conn.commit()
            print(f"✅ 修复了 {fixed_count} 条记录的 JSON 字段")
        else:
            print("✅ JSON 字段数据正常")

        conn.close()
    except Exception as e:
        print(f"⚠️ 修复JSON字段失败: {e}")


def close_db():
    """关闭数据库连接"""
    SessionLocal.remove()
