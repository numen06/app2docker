# backend/database.py
"""数据库配置和会话管理"""
import os
import uuid
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
# SessionFactory: 每次调用返回独立 Session，适用于后台任务/工具函数
# SessionLocal(scoped_session): 线程级 Session，保留给需要线程上下文复用的场景
SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionLocal = scoped_session(SessionFactory)

# 线程本地存储
_local = threading.local()

# 每个进程只执行一次 init_db 内迁移（避免 OperationLogger 等重复触发）
_init_db_lock = threading.Lock()
_init_db_done = False

DEFAULT_TEAM_NAME = "默认团队"
DEFAULT_TEAM_SLUG = "default"
MIGRATION_DEFAULT_TEAM_BACKFILL = "migration.default_team_resource_backfill_done"


def get_db():
    """获取数据库会话（用于依赖注入）"""
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """获取数据库会话（用于直接调用）"""
    # 返回独立 Session，避免 scoped_session 在同线程嵌套调用时互相影响
    return SessionFactory()


def init_db():
    """初始化数据库（创建所有表）"""
    global _init_db_done
    with _init_db_lock:
        if _init_db_done:
            return
        _run_init_db_migrations()
        _init_db_done = True


def _run_init_db_migrations():
    """实际迁移逻辑（每进程仅执行一次）。"""
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

    # 迁移：添加post_build_webhooks字段（如果不存在）
    migrate_add_post_build_webhooks()

    # 迁移：添加流水线 Tag 构建开关字段（如果不存在）
    migrate_add_pipeline_tag_build_enabled()

    # 迁移：添加Portainer相关字段到agent_hosts表（如果不存在）
    migrate_add_portainer_fields()

    # 迁移：添加Portainer认证模式相关字段
    migrate_add_portainer_auth_mode()

    # 迁移：修改token字段允许NULL（如果表已存在且token字段不允许NULL）
    migrate_token_nullable()

    # 迁移：修复JSON字段的无效数据
    migrate_fix_json_fields()

    # 迁移：添加started_at字段到tasks表（如果不存在）
    migrate_add_started_at_field()

    # 迁移：添加用户系统表
    migrate_add_user_system()

    # 迁移：创建agent_secrets表
    migrate_add_agent_secrets_table()

    # 迁移：创建 app_keys 表
    migrate_add_app_keys_table()

    # 迁移：添加agent_unique_id字段到agent_hosts表
    migrate_add_agent_unique_id()

    # 迁移：创建deploy_configs表
    migrate_add_deploy_config_table()
    migrate_deploy_task_architecture()
    migrate_init_system_settings()

    # 迁移：团队/成员/邀请表
    migrate_add_teams_tables()

    # 迁移：团队资源权限与分组
    migrate_add_team_resource_permissions()
    migrate_add_extended_resource_permissions()

    # 迁移：团队任务清理天数
    migrate_add_team_task_cleanup_days()

    # 迁移：任务/导出/主机/资源包/操作日志 team_id
    migrate_add_team_id_to_misc_tables()

    # 迁移：无 team_id 的文件上传构建任务，从操作日志/用户团队推断
    migrate_backfill_orphan_upload_build_tasks()

    # 迁移：默认团队（去重 + 确保存在 + 一次性历史 team_id 回填）
    migrate_backfill_default_team()

    # 迁移：镜像迁移任务表与菜单权限
    migrate_add_migration_tasks_table()

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


def migrate_add_post_build_webhooks():
    """迁移：为pipelines表添加post_build_webhooks字段"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pipelines'"
        )
        if not cursor.fetchone():
            conn.close()
            return

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(pipelines)")
        columns = [row[1] for row in cursor.fetchall()]

        if "post_build_webhooks" not in columns:
            print("🔄 添加 post_build_webhooks 字段到 pipelines 表...")
            # SQLite 不支持直接添加 JSON 列，这里使用 TEXT 存储 JSON 字符串
            cursor.execute(
                "ALTER TABLE pipelines ADD COLUMN post_build_webhooks TEXT DEFAULT '[]'"
            )
            conn.commit()
            print("✅ post_build_webhooks 字段添加成功")
        else:
            print("✅ post_build_webhooks 字段已存在")

        conn.close()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ post_build_webhooks 字段已存在")
        else:
            print(f"⚠️ 迁移post_build_webhooks字段失败: {e}")
    except Exception as e:
        print(f"⚠️ 迁移post_build_webhooks字段失败: {e}")


def migrate_add_pipeline_tag_build_enabled():
    """迁移：为pipelines表添加tag_build_enabled字段"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pipelines'"
        )
        if not cursor.fetchone():
            conn.close()
            return

        cursor.execute("PRAGMA table_info(pipelines)")
        columns = [row[1] for row in cursor.fetchall()]

        if "tag_build_enabled" not in columns:
            print("🔄 添加 tag_build_enabled 字段到 pipelines 表...")
            cursor.execute(
                "ALTER TABLE pipelines ADD COLUMN tag_build_enabled BOOLEAN DEFAULT 0"
            )
            conn.commit()
            print("✅ tag_build_enabled 字段添加成功")
        else:
            print("✅ tag_build_enabled 字段已存在")

        conn.close()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ tag_build_enabled 字段已存在")
        else:
            print(f"⚠️ 迁移tag_build_enabled字段失败: {e}")
    except Exception as e:
        print(f"⚠️ 迁移tag_build_enabled字段失败: {e}")


def migrate_add_portainer_fields():
    """迁移：为agent_hosts表添加Portainer相关字段"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_hosts'"
        )
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
            cursor.execute("ALTER TABLE agent_hosts ADD COLUMN portainer_api_key TEXT")
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


def migrate_add_portainer_auth_mode():
    """迁移：为 agent_hosts 表添加 Portainer 认证模式相关字段"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_hosts'"
        )
        if not cursor.fetchone():
            conn.close()
            return

        cursor.execute("PRAGMA table_info(agent_hosts)")
        columns = [row[1] for row in cursor.fetchall()]

        if "portainer_auth_mode" not in columns:
            print("🔄 添加 portainer_auth_mode 字段到 agent_hosts 表...")
            cursor.execute(
                "ALTER TABLE agent_hosts ADD COLUMN portainer_auth_mode VARCHAR(20) DEFAULT 'apiKey'"
            )
            conn.commit()
            print("✅ portainer_auth_mode 字段添加成功")

        if "portainer_username" not in columns:
            print("🔄 添加 portainer_username 字段到 agent_hosts 表...")
            cursor.execute(
                "ALTER TABLE agent_hosts ADD COLUMN portainer_username VARCHAR(255)"
            )
            conn.commit()
            print("✅ portainer_username 字段添加成功")

        if "portainer_password" not in columns:
            print("🔄 添加 portainer_password 字段到 agent_hosts 表...")
            cursor.execute(
                "ALTER TABLE agent_hosts ADD COLUMN portainer_password TEXT"
            )
            conn.commit()
            print("✅ portainer_password 字段添加成功")

        conn.close()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ Portainer 认证模式字段已存在")
        else:
            print(f"⚠️ 迁移Portainer认证模式字段失败: {e}")
    except Exception as e:
        print(f"⚠️ 迁移Portainer认证模式字段失败: {e}")


def migrate_token_nullable():
    """迁移：修改agent_hosts表的token字段允许NULL"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_hosts'"
        )
        if not cursor.fetchone():
            conn.close()
            return

        # 检查token字段的定义
        cursor.execute("PRAGMA table_info(agent_hosts)")
        columns = cursor.fetchall()

        token_column = None
        for col in columns:
            if col[1] == "token":  # col[1] 是列名
                token_column = col
                break

        if token_column:
            # col[3] 是 notnull 标志（1表示NOT NULL，0表示允许NULL）
            if token_column[3] == 1:
                print("🔄 修改 token 字段允许 NULL...")
                # SQLite不支持直接修改列约束，需要重建表
                # 1. 创建新表
                cursor.execute(
                    """
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
                """
                )

                # 2. 复制数据（明确指定列顺序，确保 JSON 字段正确）
                cursor.execute(
                    """
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
                """
                )

                # 3. 删除旧表
                cursor.execute("DROP TABLE agent_hosts")

                # 4. 重命名新表
                cursor.execute("ALTER TABLE agent_hosts_new RENAME TO agent_hosts")

                # 5. 重新创建索引
                cursor.execute(
                    "CREATE UNIQUE INDEX idx_agent_host_token ON agent_hosts(token)"
                )
                cursor.execute(
                    "CREATE INDEX idx_agent_host_status ON agent_hosts(status)"
                )
                cursor.execute("CREATE INDEX idx_agent_host_name ON agent_hosts(name)")
                cursor.execute(
                    "CREATE INDEX idx_agent_host_type ON agent_hosts(host_type)"
                )

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
            cursor.execute("ALTER TABLE tasks ADD COLUMN started_at DATETIME")
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
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_hosts'"
        )
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
                    host_info_fixed = "{}"
            except (json.JSONDecodeError, TypeError):
                # 如果不是有效的 JSON，重置为空对象
                host_info_fixed = "{}"
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
                    docker_info_fixed = "{}"
            except (json.JSONDecodeError, TypeError):
                # 如果不是有效的 JSON，重置为空对象
                docker_info_fixed = "{}"
                fixed_count += 1

            # 如果数据需要修复，更新记录
            if host_info_fixed != host_info or docker_info_fixed != docker_info:
                cursor.execute(
                    """
                    UPDATE agent_hosts 
                    SET host_info = ?, docker_info = ?
                    WHERE host_id = ?
                """,
                    (host_info_fixed, docker_info_fixed, host_id),
                )

        if fixed_count > 0:
            conn.commit()
            print(f"✅ 修复了 {fixed_count} 条记录的 JSON 字段")
        else:
            print("✅ JSON 字段数据正常")

        conn.close()
    except Exception as e:
        print(f"⚠️ 修复JSON字段失败: {e}")


def migrate_add_user_system():
    """迁移：添加用户系统表并迁移现有用户数据"""
    from backend.models import User, Role, Permission, UserRole, RolePermission, Base
    from backend.config import load_config
    from backend.auth import hash_password
    import json

    # 表已经通过Base.metadata.create_all创建，这里只需要迁移数据
    if not os.path.exists(DB_FILE):
        return

    try:
        db = get_db_session()
        try:
            # 检查users表是否存在数据
            existing_users = db.query(User).count()
            if existing_users > 0:
                print("✅ 用户系统表已存在数据，跳过迁移")
                return

            print("🔄 开始迁移用户系统...")

            # 1. 创建默认角色
            default_roles = [
                {"name": "admin", "description": "管理员，拥有所有权限"},
                {"name": "user", "description": "普通用户，拥有基础功能权限"},
                {"name": "readonly", "description": "只读用户，仅拥有查看权限"},
            ]

            role_map = {}
            for role_data in default_roles:
                role = db.query(Role).filter(Role.name == role_data["name"]).first()
                if not role:
                    role = Role(
                        role_id=str(uuid.uuid4()),
                        name=role_data["name"],
                        description=role_data["description"],
                    )
                    db.add(role)
                    db.commit()
                    print(f"✅ 创建角色: {role_data['name']}")
                role_map[role_data["name"]] = role

            # 2. 创建默认权限
            default_permissions = [
                {"code": "menu.dashboard", "name": "仪表盘", "category": "menu"},
                {"code": "menu.build", "name": "镜像构建", "category": "menu"},
                {"code": "menu.export", "name": "导出镜像", "category": "menu"},
                {"code": "menu.migration", "name": "镜像迁移", "category": "menu"},
                {"code": "menu.tasks", "name": "任务管理", "category": "menu"},
                {"code": "menu.pipeline", "name": "流水线", "category": "menu"},
                {"code": "menu.datasource", "name": "数据源", "category": "menu"},
                {"code": "menu.registry", "name": "镜像仓库", "category": "menu"},
                {"code": "menu.template", "name": "模板管理", "category": "menu"},
                {"code": "menu.resource-package", "name": "资源包", "category": "menu"},
                {"code": "menu.host", "name": "主机管理", "category": "menu"},
                {"code": "menu.docker", "name": "Docker管理", "category": "menu"},
                {"code": "menu.deploy", "name": "部署管理", "category": "menu"},
                {"code": "menu.users", "name": "用户管理", "category": "menu"},
            ]

            permission_map = {}
            for perm_data in default_permissions:
                perm = (
                    db.query(Permission)
                    .filter(Permission.code == perm_data["code"])
                    .first()
                )
                if not perm:
                    perm = Permission(
                        permission_id=str(uuid.uuid4()),
                        code=perm_data["code"],
                        name=perm_data["name"],
                        category=perm_data["category"],
                    )
                    db.add(perm)
                    db.commit()
                    print(f"✅ 创建权限: {perm_data['code']}")
                permission_map[perm_data["code"]] = perm

            # 3. 分配角色权限
            # 管理员：所有权限
            admin_role = role_map["admin"]
            for perm in permission_map.values():
                existing = (
                    db.query(RolePermission)
                    .filter(
                        RolePermission.role_id == admin_role.role_id,
                        RolePermission.permission_id == perm.permission_id,
                    )
                    .first()
                )
                if not existing:
                    rp = RolePermission(
                        role_id=admin_role.role_id, permission_id=perm.permission_id
                    )
                    db.add(rp)

            # 普通用户：除用户管理外的所有菜单权限
            user_role = role_map["user"]
            for code, perm in permission_map.items():
                if code != "menu.users":
                    existing = (
                        db.query(RolePermission)
                        .filter(
                            RolePermission.role_id == user_role.role_id,
                            RolePermission.permission_id == perm.permission_id,
                        )
                        .first()
                    )
                    if not existing:
                        rp = RolePermission(
                            role_id=user_role.role_id, permission_id=perm.permission_id
                        )
                        db.add(rp)

            # 只读用户：仅查看类菜单
            readonly_role = role_map["readonly"]
            readonly_permissions = [
                "menu.dashboard",
                "menu.tasks",
                "menu.pipeline",
                "menu.datasource",
                "menu.registry",
                "menu.template",
                "menu.resource-package",
                "menu.host",
                "menu.docker",
            ]
            for code in readonly_permissions:
                if code in permission_map:
                    perm = permission_map[code]
                    existing = (
                        db.query(RolePermission)
                        .filter(
                            RolePermission.role_id == readonly_role.role_id,
                            RolePermission.permission_id == perm.permission_id,
                        )
                        .first()
                    )
                    if not existing:
                        rp = RolePermission(
                            role_id=readonly_role.role_id,
                            permission_id=perm.permission_id,
                        )
                        db.add(rp)

            db.commit()
            print("✅ 角色权限分配完成")

            # 4. 从config.yml迁移用户
            config = load_config()
            users_config = config.get("users", {})

            # 如果没有配置用户，创建默认admin用户
            if not users_config:
                admin_password_hash = hash_password("admin")
                admin_user = User(
                    user_id=str(uuid.uuid4()),
                    username="admin",
                    password_hash=admin_password_hash,
                    enabled=True,
                )
                db.add(admin_user)
                db.commit()

                # 分配admin角色
                admin_role = role_map["admin"]
                user_role = UserRole(
                    user_id=admin_user.user_id, role_id=admin_role.role_id
                )
                db.add(user_role)
                db.commit()
                print("✅ 创建默认admin用户")
            else:
                # 迁移配置中的用户
                for username, password_hash in users_config.items():
                    user = db.query(User).filter(User.username == username).first()
                    if not user:
                        user = User(
                            user_id=str(uuid.uuid4()),
                            username=username,
                            password_hash=password_hash,
                            enabled=True,
                        )
                        db.add(user)
                        db.commit()
                        print(f"✅ 迁移用户: {username}")

                        # 分配角色：admin用户分配admin角色，其他分配user角色
                        if username == "admin":
                            role = role_map["admin"]
                        else:
                            role = role_map["user"]
                        user_role = UserRole(user_id=user.user_id, role_id=role.role_id)
                        db.add(user_role)
                        db.commit()

            print("✅ 用户系统迁移完成")
        finally:
            db.close()
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"⚠️ 迁移用户系统失败: {e}")


def migrate_add_agent_secrets_table():
    """迁移：创建agent_secrets表"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查表是否已存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_secrets'"
        )
        if cursor.fetchone():
            conn.close()
            print("✅ agent_secrets 表已存在")
            return

        # 创建表
        cursor.execute(
            """
            CREATE TABLE agent_secrets (
                secret_id VARCHAR(36) PRIMARY KEY,
                secret_key VARCHAR(64) UNIQUE NOT NULL,
                name VARCHAR(255),
                enabled BOOLEAN DEFAULT 1,
                created_at DATETIME,
                updated_at DATETIME
            )
        """
        )

        # 创建索引
        cursor.execute(
            "CREATE UNIQUE INDEX idx_agent_secret_key ON agent_secrets(secret_key)"
        )
        cursor.execute(
            "CREATE INDEX idx_agent_secret_enabled ON agent_secrets(enabled)"
        )

        conn.commit()
        conn.close()
        print("✅ agent_secrets 表创建成功")
    except sqlite3.OperationalError as e:
        if "already exists" in str(e).lower():
            print("✅ agent_secrets 表已存在")
        else:
            print(f"⚠️ 创建agent_secrets表失败: {e}")
    except Exception as e:
        print(f"⚠️ 创建agent_secrets表失败: {e}")


def migrate_add_app_keys_table():
    """迁移：创建 app_keys 表"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查表是否已存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='app_keys'"
        )
        if cursor.fetchone():
            conn.close()
            print("✅ app_keys 表已存在")
            return

        cursor.execute(
            """
            CREATE TABLE app_keys (
                key_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                name VARCHAR(255) NOT NULL,
                key_hash VARCHAR(64) UNIQUE NOT NULL,
                key_prefix VARCHAR(16) NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                last_used_at DATETIME,
                expires_at DATETIME,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """
        )

        cursor.execute("CREATE INDEX idx_app_key_user ON app_keys(user_id)")
        cursor.execute("CREATE UNIQUE INDEX idx_app_key_hash ON app_keys(key_hash)")
        cursor.execute("CREATE INDEX idx_app_key_enabled ON app_keys(enabled)")

        conn.commit()
        conn.close()
        print("✅ app_keys 表创建成功")
    except sqlite3.OperationalError as e:
        if "already exists" in str(e).lower():
            print("✅ app_keys 表已存在")
        else:
            print(f"⚠️ 创建app_keys表失败: {e}")
    except Exception as e:
        print(f"⚠️ 创建app_keys表失败: {e}")


def migrate_add_agent_unique_id():
    """迁移：为agent_hosts表添加agent_unique_id字段"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_hosts'"
        )
        if not cursor.fetchone():
            conn.close()
            return

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(agent_hosts)")
        columns = [row[1] for row in cursor.fetchall()]

        if "agent_unique_id" not in columns:
            print("🔄 添加 agent_unique_id 字段到 agent_hosts 表...")
            cursor.execute(
                "ALTER TABLE agent_hosts ADD COLUMN agent_unique_id VARCHAR(128)"
            )
            # 创建索引
            cursor.execute(
                "CREATE INDEX idx_agent_host_unique_id ON agent_hosts(agent_unique_id)"
            )
            conn.commit()
            print("✅ agent_unique_id 字段添加成功")
        else:
            print("✅ agent_unique_id 字段已存在")

        conn.close()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✅ agent_unique_id 字段已存在")
        else:
            print(f"⚠️ 迁移agent_unique_id字段失败: {e}")
    except Exception as e:
        print(f"⚠️ 迁移agent_unique_id字段失败: {e}")


def migrate_add_deploy_config_table():
    """迁移：创建deploy_configs表（如果不存在）"""
    # 表已经通过Base.metadata.create_all创建，这里主要是确保表存在
    # 如果需要迁移现有数据，可以在这里添加迁移逻辑
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 检查表是否已存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='deploy_configs'"
        )
        if cursor.fetchone():
            conn.close()
            print("✅ deploy_configs 表已存在")
            return

        # 表不存在时会通过Base.metadata.create_all创建，这里只做检查
        conn.close()
        print("✅ deploy_configs 表将在表创建时自动创建")
    except Exception as e:
        print(f"⚠️ 检查deploy_configs表失败: {e}")


def migrate_deploy_task_architecture():
    """迁移：重构部署任务架构，将配置任务迁移到 DeployConfig 表"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        # 1. 添加 deploy_config_id 字段到 tasks 表（如果不存在）
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN deploy_config_id VARCHAR(36)")
            conn.commit()
            print("✅ 已添加 deploy_config_id 字段到 tasks 表")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("✅ deploy_config_id 字段已存在")
            else:
                print(f"⚠️ 添加 deploy_config_id 字段失败: {e}")
                conn.rollback()
                return
        except Exception as e:
            print(f"⚠️ 添加 deploy_config_id 字段失败: {e}")
            conn.rollback()
            return

        # 2. 检查是否有需要迁移的数据
        # 只迁移真正的配置任务：task_type='deploy' 且没有 source_config_id 且没有 deploy_config_id
        cursor.execute("""
            SELECT COUNT(*) FROM tasks 
            WHERE task_type = 'deploy' 
            AND (deploy_config_id IS NULL)
            AND (task_config IS NOT NULL AND json_extract(task_config, '$.source_config_id') IS NULL)
        """)
        config_task_count = cursor.fetchone()[0]

        if config_task_count == 0:
            print("✅ 没有需要迁移的配置任务")
            conn.close()
            return

        print(f"🔄 开始迁移 {config_task_count} 个配置任务到 DeployConfig 表...")

        # 3. 查询所有配置任务（task_type="deploy" 且没有 source_config_id 且没有 deploy_config_id）
        cursor.execute("""
            SELECT task_id, task_config, tag, created_at
            FROM tasks 
            WHERE task_type = 'deploy' 
            AND (deploy_config_id IS NULL)
            AND (task_config IS NOT NULL AND json_extract(task_config, '$.source_config_id') IS NULL)
        """)
        config_tasks = cursor.fetchall()

        migrated_count = 0
        for task_id, task_config_json, tag, created_at in config_tasks:
            try:
                import json
                task_config = json.loads(task_config_json) if task_config_json else {}

                # 提取配置信息
                config_content = task_config.get("config_content", "")
                registry = task_config.get("registry")
                webhook_token = task_config.get("webhook_token")
                webhook_secret = task_config.get("webhook_secret")
                webhook_branch_strategy = task_config.get("webhook_branch_strategy")
                webhook_allowed_branches = task_config.get("webhook_allowed_branches")
                config = task_config.get("config", {})

                # 从配置中提取应用名称
                app_name = config.get("app", {}).get("name") if isinstance(config.get("app"), dict) else config.get("app_name", "")
                if not app_name:
                    # 如果没有应用名称，使用 task_id 的前8位
                    app_name = f"deploy-{task_id[:8]}"

                # 检查应用名称是否已存在（DeployConfig 表有唯一约束）
                cursor.execute("SELECT config_id FROM deploy_configs WHERE app_name = ?", (app_name,))
                existing = cursor.fetchone()
                if existing:
                    # 如果已存在，检查是否已经有相同的配置内容
                    existing_config_id = existing[0]
                    cursor.execute("SELECT config_content FROM deploy_configs WHERE config_id = ?", (existing_config_id,))
                    existing_config = cursor.fetchone()
                    if existing_config and existing_config[0] == config_content:
                        # 配置内容相同，直接使用现有的配置，更新执行任务的关联
                        print(f"  ⚠️ 配置已存在，跳过迁移: {task_id[:8]} -> {existing_config_id[:8]} (app_name: {app_name})")
                        # 更新执行任务的 deploy_config_id（如果有）
                        cursor.execute("""
                            UPDATE tasks 
                            SET deploy_config_id = ?
                            WHERE task_type = 'deploy' 
                            AND task_config IS NOT NULL 
                            AND json_extract(task_config, '$.source_config_id') = ?
                        """, (existing_config_id, task_id))
                        # 删除原配置任务
                        cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
                        migrated_count += 1
                        continue
                    else:
                        # 配置内容不同，使用 task_id 作为后缀
                        app_name = f"{app_name}-{task_id[:8]}"

                # 创建 DeployConfig 记录
                config_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO deploy_configs (
                        config_id, app_name, config_content, config_json, 
                        registry, tag, webhook_token, webhook_secret,
                        webhook_branch_strategy, webhook_allowed_branches,
                        execution_count, last_executed_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config_id,
                    app_name,
                    config_content,
                    json.dumps(config),
                    registry,
                    tag,
                    webhook_token,
                    webhook_secret,
                    webhook_branch_strategy,
                    json.dumps(webhook_allowed_branches) if webhook_allowed_branches else None,
                    0,  # execution_count
                    None,  # last_executed_at
                    created_at,
                    created_at,  # updated_at
                ))

                # 4. 更新所有执行任务（有 source_config_id 指向此配置的任务）
                cursor.execute("""
                    UPDATE tasks 
                    SET deploy_config_id = ?
                    WHERE task_type = 'deploy' 
                    AND task_config IS NOT NULL 
                    AND json_extract(task_config, '$.source_config_id') = ?
                """, (config_id, task_id))

                # 5. 删除原配置任务（已迁移到 DeployConfig 表）
                cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))

                migrated_count += 1
                print(f"  ✅ 迁移配置任务: {task_id[:8]} -> {config_id[:8]} (app_name: {app_name})")

            except Exception as e:
                print(f"  ⚠️ 迁移配置任务 {task_id[:8]} 失败: {e}")
                import traceback
                traceback.print_exc()
                continue

        conn.commit()
        print(f"✅ 迁移完成：共迁移 {migrated_count} 个配置任务")

        # 6. 创建索引（如果不存在）
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_deploy_config ON tasks(deploy_config_id)")
            conn.commit()
            print("✅ 已创建 deploy_config_id 索引")
        except Exception as e:
            print(f"⚠️ 创建索引失败: {e}")

        conn.close()

    except Exception as e:
        print(f"⚠️ 迁移部署任务架构失败: {e}")
        import traceback
        traceback.print_exc()


def migrate_init_system_settings():
    """迁移：初始化系统设置默认值"""
    if not os.path.exists(DB_FILE):
        return
    try:
        from backend.task_queue_manager import GlobalTaskQueueManager

        GlobalTaskQueueManager().ensure_defaults()
        print("✅ system_settings 默认配置已初始化")
    except Exception as e:
        print(f"⚠️ 初始化 system_settings 失败: {e}")


def migrate_add_teams_tables():
    """迁移：创建 teams / team_members / team_invitations 表"""
    if not os.path.exists(DB_FILE):
        return
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='teams'"
        )
        if not cursor.fetchone():
            print("🔄 创建 teams 表...")
            cursor.execute(
                """
                CREATE TABLE teams (
                    team_id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(255) NOT NULL UNIQUE,
                    description TEXT DEFAULT '',
                    avatar_url VARCHAR(512),
                    created_by VARCHAR(36) NOT NULL,
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY(created_by) REFERENCES users(user_id)
                )
            """
            )
            cursor.execute("CREATE INDEX idx_team_slug ON teams(slug)")
            conn.commit()
            print("✅ teams 表创建成功")
        else:
            print("✅ teams 表已存在")

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='team_members'"
        )
        if not cursor.fetchone():
            print("🔄 创建 team_members 表...")
            cursor.execute(
                """
                CREATE TABLE team_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'member',
                    joined_at DATETIME,
                    FOREIGN KEY(team_id) REFERENCES teams(team_id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id),
                    UNIQUE(team_id, user_id)
                )
            """
            )
            cursor.execute(
                "CREATE INDEX idx_team_member_team ON team_members(team_id)"
            )
            cursor.execute(
                "CREATE INDEX idx_team_member_user ON team_members(user_id)"
            )
            conn.commit()
            print("✅ team_members 表创建成功")
        else:
            print("✅ team_members 表已存在")

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='team_invitations'"
        )
        if not cursor.fetchone():
            print("🔄 创建 team_invitations 表...")
            cursor.execute(
                """
                CREATE TABLE team_invitations (
                    invitation_id VARCHAR(36) PRIMARY KEY,
                    team_id VARCHAR(36) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'member',
                    token VARCHAR(64) NOT NULL UNIQUE,
                    invited_by VARCHAR(36) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    accepted_at DATETIME,
                    created_at DATETIME,
                    FOREIGN KEY(team_id) REFERENCES teams(team_id),
                    FOREIGN KEY(invited_by) REFERENCES users(user_id)
                )
            """
            )
            cursor.execute(
                "CREATE INDEX idx_team_invitation_team ON team_invitations(team_id)"
            )
            cursor.execute(
                "CREATE INDEX idx_team_invitation_token ON team_invitations(token)"
            )
            conn.commit()
            print("✅ team_invitations 表创建成功")
        else:
            print("✅ team_invitations 表已存在")

        conn.close()
    except Exception as e:
        print(f"⚠️ 创建团队相关表失败: {e}")


def migrate_add_team_resource_permissions():
    """迁移：资源 team_id、权限表、分组表"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        resource_tables = [
            ("pipelines", "team_id VARCHAR(36)"),
            ("pipelines", "group_id VARCHAR(36)"),
            ("pipelines", "created_by VARCHAR(36)"),
            ("deploy_configs", "team_id VARCHAR(36)"),
            ("deploy_configs", "created_by VARCHAR(36)"),
            ("git_sources", "team_id VARCHAR(36)"),
            ("git_sources", "created_by VARCHAR(36)"),
            ("agent_hosts", "team_id VARCHAR(36)"),
            ("agent_hosts", "group_id VARCHAR(36)"),
            ("agent_hosts", "created_by VARCHAR(36)"),
        ]
        for table, col_def in resource_tables:
            col_name = col_def.split()[0]
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            if cursor.fetchone():
                _add_column_if_missing(cursor, table, col_name, col_def)

        new_tables = {
            "pipeline_permissions": """
                CREATE TABLE pipeline_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pipeline_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    permission VARCHAR(20) NOT NULL DEFAULT 'view',
                    granted_by VARCHAR(36),
                    created_at DATETIME,
                    UNIQUE(pipeline_id, user_id)
                )
            """,
            "host_permissions": """
                CREATE TABLE host_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    host_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    permission VARCHAR(20) NOT NULL DEFAULT 'view',
                    granted_by VARCHAR(36),
                    created_at DATETIME,
                    UNIQUE(host_id, user_id)
                )
            """,
            "deploy_config_permissions": """
                CREATE TABLE deploy_config_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    permission VARCHAR(20) NOT NULL DEFAULT 'view',
                    granted_by VARCHAR(36),
                    created_at DATETIME,
                    UNIQUE(config_id, user_id)
                )
            """,
            "git_source_permissions": """
                CREATE TABLE git_source_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    permission VARCHAR(20) NOT NULL DEFAULT 'view',
                    granted_by VARCHAR(36),
                    created_at DATETIME,
                    UNIQUE(source_id, user_id)
                )
            """,
            "pipeline_groups": """
                CREATE TABLE pipeline_groups (
                    group_id VARCHAR(36) PRIMARY KEY,
                    team_id VARCHAR(36) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT DEFAULT '',
                    created_at DATETIME
                )
            """,
            "pipeline_group_permissions": """
                CREATE TABLE pipeline_group_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    permission VARCHAR(20) NOT NULL DEFAULT 'view',
                    granted_by VARCHAR(36),
                    created_at DATETIME,
                    UNIQUE(group_id, user_id)
                )
            """,
            "host_groups": """
                CREATE TABLE host_groups (
                    group_id VARCHAR(36) PRIMARY KEY,
                    team_id VARCHAR(36) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT DEFAULT '',
                    created_at DATETIME
                )
            """,
            "host_group_permissions": """
                CREATE TABLE host_group_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    permission VARCHAR(20) NOT NULL DEFAULT 'view',
                    granted_by VARCHAR(36),
                    created_at DATETIME,
                    UNIQUE(group_id, user_id)
                )
            """,
        }

        for table_name, ddl in new_tables.items():
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            if not cursor.fetchone():
                print(f"🔄 创建 {table_name} 表...")
                cursor.execute(ddl)
                print(f"✅ {table_name} 表创建成功")

        conn.commit()
        conn.close()
        print("✅ 团队资源权限迁移完成")
    except Exception as e:
        print(f"⚠️ 团队资源权限迁移失败: {e}")


def migrate_add_extended_resource_permissions():
    """迁移：资源包/镜像仓库/模板权限表及 docker_registries、template_records"""
    if not os.path.exists(DB_FILE):
        return

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()

        new_tables = {
            "resource_package_permissions": """
                CREATE TABLE resource_package_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    permission VARCHAR(20) NOT NULL DEFAULT 'view',
                    granted_by VARCHAR(36),
                    created_at DATETIME,
                    UNIQUE(package_id, user_id)
                )
            """,
            "docker_registries": """
                CREATE TABLE docker_registries (
                    registry_id VARCHAR(36) PRIMARY KEY,
                    team_id VARCHAR(36),
                    created_by VARCHAR(36),
                    name VARCHAR(255) NOT NULL,
                    registry VARCHAR(255) NOT NULL DEFAULT 'docker.io',
                    registry_prefix VARCHAR(255) DEFAULT '',
                    username VARCHAR(255) DEFAULT '',
                    password TEXT DEFAULT '',
                    active INTEGER DEFAULT 0,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """,
            "registry_permissions": """
                CREATE TABLE registry_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registry_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    permission VARCHAR(20) NOT NULL DEFAULT 'view',
                    granted_by VARCHAR(36),
                    created_at DATETIME,
                    UNIQUE(registry_id, user_id)
                )
            """,
            "template_records": """
                CREATE TABLE template_records (
                    template_id VARCHAR(36) PRIMARY KEY,
                    team_id VARCHAR(36),
                    created_by VARCHAR(36),
                    name VARCHAR(255) NOT NULL,
                    project_type VARCHAR(64) NOT NULL DEFAULT 'jar',
                    file_path VARCHAR(512) NOT NULL,
                    template_type VARCHAR(32) NOT NULL DEFAULT 'user',
                    created_at DATETIME,
                    updated_at DATETIME,
                    UNIQUE(team_id, name)
                )
            """,
            "template_permissions": """
                CREATE TABLE template_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id VARCHAR(36) NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    permission VARCHAR(20) NOT NULL DEFAULT 'view',
                    granted_by VARCHAR(36),
                    created_at DATETIME,
                    UNIQUE(template_id, user_id)
                )
            """,
        }

        for table_name, ddl in new_tables.items():
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            if not cursor.fetchone():
                print(f"🔄 创建 {table_name} 表...")
                cursor.execute(ddl)
                print(f"✅ {table_name} 表创建成功")

        conn.commit()
        conn.close()
        migrate_registries_from_config_to_db()
        migrate_user_templates_to_records()
        print("✅ 扩展资源权限迁移完成")
    except Exception as e:
        print(f"⚠️ 扩展资源权限迁移失败: {e}")


def migrate_registries_from_config_to_db():
    """将 config 中的 registries 按团队补全到 docker_registries（团队维度幂等）"""
    try:
        from backend.registry_manager import (
            _config_registry_entries,
            ensure_team_registries_from_config,
        )
        from backend.database import get_db_session
        from backend.models import Team, TeamMember

        if not _config_registry_entries():
            return

        db = get_db_session()
        try:
            teams = db.query(Team).order_by(Team.created_at.asc()).all()
            if not teams:
                print("⚠️ 镜像仓库 config 迁移跳过：尚无团队")
                return

            total = 0
            for team in teams:
                if not team.team_id:
                    continue
                created_by = team.created_by or None
                if not created_by:
                    member = (
                        db.query(TeamMember.user_id)
                        .filter(TeamMember.team_id == team.team_id)
                        .order_by(TeamMember.joined_at.asc())
                        .first()
                    )
                    created_by = member[0] if member else None
                if not created_by:
                    print(
                        f"⚠️ 镜像仓库 config 迁移跳过团队 {team.team_id}：无可用创建者"
                    )
                    continue
                total += ensure_team_registries_from_config(
                    team.team_id, created_by
                )
            if total:
                print(f"✅ 启动迁移：共为团队写入 {total} 条镜像仓库")
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ 镜像仓库 config 迁移失败: {e}")


def migrate_user_templates_to_records():
    """将已有用户模板文件同步到 template_records（仅当表为空时）"""
    try:
        import os
        from backend.handlers import USER_TEMPLATES_DIR, get_all_templates
        from backend.database import get_db_session
        from backend.models import TemplateRecord, Team

        db = get_db_session()
        try:
            if db.query(TemplateRecord).count() > 0:
                return
            team = db.query(Team).order_by(Team.created_at.asc()).first()
            team_id = team.team_id if team else None
            templates = get_all_templates()
            count = 0
            for name, info in templates.items():
                if info.get("type") != "user":
                    continue
                path = info.get("path")
                if not path or not os.path.exists(path):
                    continue
                existing = (
                    db.query(TemplateRecord)
                    .filter(
                        TemplateRecord.team_id == team_id,
                        TemplateRecord.name == name,
                    )
                    .first()
                )
                if existing:
                    continue
                db.add(
                    TemplateRecord(
                        template_id=str(uuid.uuid4()),
                        team_id=team_id,
                        name=name,
                        project_type=info.get("project_type", "jar"),
                        file_path=path,
                        template_type="user",
                    )
                )
                count += 1
            if count:
                db.commit()
                print(f"✅ 已同步 {count} 条用户模板元数据")
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ 用户模板元数据迁移失败: {e}")


def _add_column_if_missing(cursor, table: str, column: str, ddl: str):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        print(f"🔄 添加 {column} 字段到 {table} 表...")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        print(f"✅ {column} 字段添加成功")
    else:
        print(f"✅ {table}.{column} 已存在")


def migrate_add_team_task_cleanup_days():
    """迁移：为 teams 表添加 task_cleanup_days 字段"""
    if not os.path.exists(DB_FILE):
        return
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()
        _add_column_if_missing(
            cursor,
            "teams",
            "task_cleanup_days",
            "task_cleanup_days INTEGER DEFAULT 7",
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ 迁移 task_cleanup_days 字段失败: {e}")


def migrate_add_team_id_to_misc_tables():
    """迁移：为 tasks / export_tasks / hosts / resource_packages / operation_logs 添加 team_id 等字段"""
    if not os.path.exists(DB_FILE):
        return
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        cursor = conn.cursor()
        columns = [
            ("tasks", "team_id", "team_id VARCHAR(36)"),
            ("export_tasks", "team_id", "team_id VARCHAR(36)"),
            ("hosts", "team_id", "team_id VARCHAR(36)"),
            ("hosts", "created_by", "created_by VARCHAR(36)"),
            ("resource_packages", "team_id", "team_id VARCHAR(36)"),
            ("resource_packages", "created_by", "created_by VARCHAR(36)"),
            ("operation_logs", "team_id", "team_id VARCHAR(36)"),
        ]
        for table, col, ddl in columns:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            if cursor.fetchone():
                _add_column_if_missing(cursor, table, col, ddl)
        conn.commit()
        conn.close()
        print("✅ 杂项表 team_id 字段迁移完成")
    except Exception as e:
        print(f"⚠️ 杂项表 team_id 迁移失败: {e}")


def migrate_backfill_orphan_upload_build_tasks():
    """迁移：为 team_id 为空的文件上传构建任务回填团队（优先操作日志，其次创建者所属团队）"""
    if not os.path.exists(DB_FILE):
        return

    from backend.models import OperationLog, Task, TeamMember, User

    db = get_db_session()
    try:
        orphans = (
            db.query(Task)
            .filter(
                Task.team_id.is_(None),
                Task.task_type == "build",
                Task.source == "文件上传",
            )
            .all()
        )
        if not orphans:
            return

        updated = 0
        for task in orphans:
            resolved_team_id = None

            logs = (
                db.query(OperationLog)
                .filter(OperationLog.action == "build")
                .order_by(OperationLog.timestamp.desc())
                .limit(200)
                .all()
            )
            for log in logs:
                details = log.details if isinstance(log.details, dict) else {}
                if details.get("task_id") != task.task_id:
                    continue
                if log.team_id:
                    resolved_team_id = log.team_id
                    break
                if log.username and not resolved_team_id:
                    user = (
                        db.query(User)
                        .filter(User.username == log.username)
                        .first()
                    )
                    if user:
                        member = (
                            db.query(TeamMember)
                            .filter(TeamMember.user_id == user.user_id)
                            .order_by(TeamMember.joined_at.asc())
                            .first()
                        )
                        if member:
                            resolved_team_id = member.team_id
                break

            cfg = task.task_config if isinstance(task.task_config, dict) else {}
            if not resolved_team_id and isinstance(cfg, dict) and cfg.get("team_id"):
                resolved_team_id = cfg.get("team_id")

            if not resolved_team_id:
                continue

            task.team_id = resolved_team_id
            if isinstance(cfg, dict):
                task.task_config = {**cfg, "team_id": resolved_team_id}
            updated += 1

        if updated:
            db.commit()
            print(f"🔄 文件上传构建任务: 回填 {updated} 条 team_id")
    except Exception as e:
        db.rollback()
        print(f"⚠️ 文件上传构建任务 team_id 回填失败: {e}")
    finally:
        db.close()


_DEFAULT_TEAM_RESOURCE_TABLES = (
    "pipelines",
    "deploy_configs",
    "git_sources",
    "agent_hosts",
    "hosts",
    "resource_packages",
    "tasks",
    "export_tasks",
    "operation_logs",
)


def _migration_flag_get(cursor: sqlite3.Cursor, key: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='system_settings'"
    )
    if not cursor.fetchone():
        return False
    cursor.execute(
        "SELECT setting_value FROM system_settings WHERE setting_key = ?",
        (key,),
    )
    row = cursor.fetchone()
    if not row:
        return False
    return str(row[0]).strip().lower() in ("1", "true", "yes", "done")


def _migration_flag_set(cursor: sqlite3.Cursor, key: str, description: str) -> None:
    from datetime import datetime

    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    cursor.execute(
        """
        INSERT INTO system_settings (setting_key, setting_value, description, updated_at)
        VALUES (?, '1', ?, ?)
        ON CONFLICT(setting_key) DO UPDATE SET
            setting_value = '1',
            description = excluded.description,
            updated_at = excluded.updated_at
        """,
        (key, description, now),
    )


def _repoint_team_id_refs(cursor: sqlite3.Cursor, keep_id: str, dup_id: str) -> None:
    for table in _DEFAULT_TEAM_RESOURCE_TABLES:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        if not cursor.fetchone():
            continue
        cursor.execute(f"PRAGMA table_info({table})")
        if "team_id" not in [row[1] for row in cursor.fetchall()]:
            continue
        cursor.execute(
            f"UPDATE {table} SET team_id = ? WHERE team_id = ?",
            (keep_id, dup_id),
        )
        if cursor.rowcount:
            print(f"🔄 {table}: 从重复团队迁移 {cursor.rowcount} 条")


def _dedupe_default_teams_locked(cursor: sqlite3.Cursor):
    """在 BEGIN IMMEDIATE 事务内合并重复「默认团队」，返回保留的 team_id。"""
    cursor.execute(
        "SELECT team_id, slug FROM teams WHERE slug = ? LIMIT 1",
        (DEFAULT_TEAM_SLUG,),
    )
    row = cursor.fetchone()
    if row:
        keep_id = row[0]
    else:
        cursor.execute(
            """
            SELECT team_id, slug FROM teams WHERE name = ?
            ORDER BY created_at ASC LIMIT 1
            """,
            (DEFAULT_TEAM_NAME,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        keep_id = row[0]
        if row[1] != DEFAULT_TEAM_SLUG:
            cursor.execute(
                "SELECT 1 FROM teams WHERE slug = ? LIMIT 1",
                (DEFAULT_TEAM_SLUG,),
            )
            if not cursor.fetchone():
                cursor.execute(
                    "UPDATE teams SET slug = ? WHERE team_id = ?",
                    (DEFAULT_TEAM_SLUG, keep_id),
                )
                print(f"🔄 已将团队 slug 规范为 {DEFAULT_TEAM_SLUG}")

    cursor.execute(
        "SELECT team_id FROM teams WHERE name = ? AND team_id != ?",
        (DEFAULT_TEAM_NAME, keep_id),
    )
    dup_ids = [r[0] for r in cursor.fetchall()]
    for dup_id in dup_ids:
        cursor.execute(
            """
            SELECT user_id, role FROM team_members WHERE team_id = ?
            """,
            (dup_id,),
        )
        for user_id, role in cursor.fetchall():
            cursor.execute(
                """
                SELECT id, role FROM team_members
                WHERE team_id = ? AND user_id = ?
                """,
                (keep_id, user_id),
            )
            existing = cursor.fetchone()
            if existing:
                if role == "owner" and existing[1] != "owner":
                    cursor.execute(
                        "UPDATE team_members SET role = 'owner' WHERE id = ?",
                        (existing[0],),
                    )
                cursor.execute(
                    "DELETE FROM team_members WHERE team_id = ? AND user_id = ?",
                    (dup_id, user_id),
                )
            else:
                cursor.execute(
                    "UPDATE team_members SET team_id = ? WHERE team_id = ? AND user_id = ?",
                    (keep_id, dup_id, user_id),
                )
        cursor.execute("DELETE FROM team_members WHERE team_id = ?", (dup_id,))
        _repoint_team_id_refs(cursor, keep_id, dup_id)
        cursor.execute("DELETE FROM teams WHERE team_id = ?", (dup_id,))
        print(f"🔄 已合并重复默认团队 ({dup_id}) -> {keep_id}")

    if dup_ids:
        print(f"✅ 默认团队去重完成，保留 {keep_id}")
    return keep_id


def _ensure_canonical_default_team_locked(
    cursor: sqlite3.Cursor, owner_user_id: str
) -> str:
    """在锁内确保存在唯一 canonical 默认团队（先 dedupe 再按需创建）。"""
    keep_id = _dedupe_default_teams_locked(cursor)
    if keep_id:
        print(f"✅ 默认团队已存在 ({keep_id})")
        return keep_id

    from datetime import datetime

    team_id = str(uuid.uuid4())
    now = datetime.now()
    cursor.execute(
        """
        INSERT INTO teams (
            team_id, name, slug, description, created_by,
            created_at, updated_at, task_cleanup_days
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 7)
        """,
        (
            team_id,
            DEFAULT_TEAM_NAME,
            DEFAULT_TEAM_SLUG,
            "系统升级时自动创建，承接历史数据",
            owner_user_id,
            now,
            now,
        ),
    )
    print(f"🔄 已创建默认团队: {DEFAULT_TEAM_NAME} ({team_id})")
    return team_id


def _backfill_null_team_ids_locked(cursor: sqlite3.Cursor, team_id: str) -> int:
    total_updated = 0
    for table in _DEFAULT_TEAM_RESOURCE_TABLES:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        if not cursor.fetchone():
            continue
        cursor.execute(f"PRAGMA table_info({table})")
        if "team_id" not in [row[1] for row in cursor.fetchall()]:
            continue
        cursor.execute(
            f"UPDATE {table} SET team_id = ? WHERE team_id IS NULL",
            (team_id,),
        )
        n = cursor.rowcount
        if n:
            print(f"🔄 {table}: 回填 {n} 条记录的 team_id")
            total_updated += n

    cursor.execute(
        """
        UPDATE tasks
        SET team_id = (
            SELECT p.team_id FROM pipelines p
            WHERE p.pipeline_id = tasks.pipeline_id AND p.team_id IS NOT NULL
        )
        WHERE team_id IS NULL AND pipeline_id IS NOT NULL
        """
    )
    if cursor.rowcount:
        print(f"🔄 tasks: 从流水线继承 {cursor.rowcount} 条 team_id")
        total_updated += cursor.rowcount

    cursor.execute(
        """
        UPDATE tasks
        SET team_id = (
            SELECT d.team_id FROM deploy_configs d
            WHERE d.config_id = tasks.deploy_config_id AND d.team_id IS NOT NULL
        )
        WHERE team_id IS NULL AND deploy_config_id IS NOT NULL
        """
    )
    if cursor.rowcount:
        print(f"🔄 tasks: 从部署配置继承 {cursor.rowcount} 条 team_id")
        total_updated += cursor.rowcount

    cursor.execute(
        "UPDATE tasks SET team_id = ? WHERE team_id IS NULL", (team_id,)
    )
    if cursor.rowcount:
        print(f"🔄 tasks: 默认团队回填 {cursor.rowcount} 条")
        total_updated += cursor.rowcount
    return total_updated


def migrate_backfill_default_team():
    """迁移：去重并确保唯一默认团队；超级管理员加入；历史 team_id 仅回填一次。"""
    if not os.path.exists(DB_FILE):
        return

    from datetime import datetime

    from backend.models import Role, TeamMember, User, UserRole

    db = get_db_session()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            print("⚠️ 未找到 admin 角色，跳过默认团队回填")
            return

        admin_user_ids = [
            row[0]
            for row in db.query(UserRole.user_id)
            .filter(UserRole.role_id == admin_role.role_id)
            .all()
        ]
        if not admin_user_ids:
            print("⚠️ 无超级管理员用户，跳过默认团队回填")
            return

        admin_users = (
            db.query(User)
            .filter(User.user_id.in_(admin_user_ids), User.enabled.is_(True))
            .order_by(User.created_at.asc())
            .all()
        )
        if not admin_users:
            print("⚠️ 无可用超级管理员账号，跳过默认团队回填")
            return

        owner_user = next(
            (u for u in admin_users if u.username == "admin"), admin_users[0]
        )
    finally:
        db.close()

    team_id = None
    conn = sqlite3.connect(DB_FILE, timeout=60.0)
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()
        team_id = _ensure_canonical_default_team_locked(
            cursor, owner_user.user_id
        )
        if _migration_flag_get(cursor, MIGRATION_DEFAULT_TEAM_BACKFILL):
            conn.execute("COMMIT")
        else:
            total = _backfill_null_team_ids_locked(cursor, team_id)
            _migration_flag_set(
                cursor,
                MIGRATION_DEFAULT_TEAM_BACKFILL,
                "默认团队历史资源 team_id 已回填",
            )
            conn.execute("COMMIT")
            if total:
                print(f"✅ 默认团队数据回填完成，共更新 {total} 条")
            else:
                print("✅ 无需回填 team_id（数据已归属团队）")
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        import traceback

        traceback.print_exc()
        print(f"⚠️ 默认团队回填失败: {e}")
        return
    finally:
        conn.close()

    db = get_db_session()
    try:
        for user in admin_users:
            existing = (
                db.query(TeamMember)
                .filter(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id == user.user_id,
                )
                .first()
            )
            if existing:
                if existing.role != "owner":
                    existing.role = "owner"
                continue
            db.add(
                TeamMember(
                    team_id=team_id,
                    user_id=user.user_id,
                    role="owner",
                    joined_at=datetime.now(),
                )
            )
            print(f"✅ 已将超级管理员 {user.username} 加入默认团队 (owner)")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ 默认团队成员同步失败: {e}")
    finally:
        db.close()


def migrate_dedupe_default_teams():
    """合并重复的「默认团队」（供手动迁移；常规启动已包含在 migrate_backfill_default_team）。"""
    if not os.path.exists(DB_FILE):
        return
    conn = sqlite3.connect(DB_FILE, timeout=60.0)
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()
        _dedupe_default_teams_locked(cursor)
        conn.execute("COMMIT")
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        print(f"⚠️ 默认团队去重失败: {e}")
    finally:
        conn.close()


def migrate_add_migration_tasks_table():
    """迁移：镜像迁移任务表及 menu.migration 权限（已有库升级）。"""
    if not os.path.exists(DB_FILE):
        return

    try:
        from backend.models import Base, MigrationTask, Permission, Role, RolePermission

        Base.metadata.create_all(bind=engine, tables=[MigrationTask.__table__])

        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(migration_tasks)")
            cols = {row[1] for row in cursor.fetchall()}
            if "source_registry_name" not in cols:
                cursor.execute(
                    "ALTER TABLE migration_tasks ADD COLUMN source_registry_name VARCHAR(255) DEFAULT ''"
                )
            if "target_registry_name" not in cols:
                cursor.execute(
                    "ALTER TABLE migration_tasks ADD COLUMN target_registry_name VARCHAR(255) DEFAULT ''"
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f"⚠️ 创建 migration_tasks 表失败: {e}")
        return

    db = SessionLocal()
    try:
        perm = db.query(Permission).filter(Permission.code == "menu.migration").first()
        if not perm:
            perm = Permission(
                permission_id=str(uuid.uuid4()),
                code="menu.migration",
                name="镜像迁移",
                category="menu",
            )
            db.add(perm)
            db.commit()
            print("✅ 创建权限: menu.migration")
        else:
            db.commit()

        for role_name in ("admin", "user"):
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                continue
            existing = (
                db.query(RolePermission)
                .filter(
                    RolePermission.role_id == role.role_id,
                    RolePermission.permission_id == perm.permission_id,
                )
                .first()
            )
            if not existing:
                db.add(
                    RolePermission(
                        role_id=role.role_id, permission_id=perm.permission_id
                    )
                )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"⚠️ 镜像迁移权限迁移失败: {e}")
    finally:
        db.close()


def close_db():
    """关闭数据库连接"""
    SessionLocal.remove()
