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

    # 迁移：添加post_build_webhooks字段（如果不存在）
    migrate_add_post_build_webhooks()

    # 迁移：添加Portainer相关字段到agent_hosts表（如果不存在）
    migrate_add_portainer_fields()

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

    # 迁移：添加agent_unique_id字段到agent_hosts表
    migrate_add_agent_unique_id()

    # 迁移：创建deploy_configs表
    migrate_add_deploy_config_table()
    migrate_deploy_task_architecture()

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


def close_db():
    """关闭数据库连接"""
    SessionLocal.remove()
