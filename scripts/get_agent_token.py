#!/usr/bin/env python3
"""
获取 Agent Token 脚本
用于获取或创建 Agent Host 的 Token，方便调试使用
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent_host_manager import AgentHostManager
from backend.database import init_db

def main():
    """获取或创建 Agent Token"""
    # 初始化数据库
    init_db()
    
    manager = AgentHostManager()
    
    # 查找名为 "本地主机" 或 "Local Host" 的 agent host
    hosts = manager.list_agent_hosts()
    
    local_host = None
    print(f"找到 {len(hosts)} 个 Agent Host:")
    for host in hosts:
        print(f"  - {host.get('name')}: token={host.get('token')}, status={host.get('status')}")
        if host.get("name") in ["本地主机", "Local Host", "local"]:
            local_host = host
            break
    
    # 如果没有找到本地主机，尝试找第一个有有效 token 的 agent 类型主机
    if not local_host:
        for host in hosts:
            if host.get("host_type") == "agent" and host.get("token") and host.get("token") != "offline":
                local_host = host
                print(f"使用找到的第一个有效 Agent Host: {host.get('name')}")
                break
    
    # 检查 token 是否有效
    token = local_host.get("token") if local_host else None
    if not token or token == "offline":
        # 如果本地主机存在但 token 无效，删除它
        if local_host and local_host.get("name") == "本地主机":
            try:
                manager.delete_agent_host(local_host.get("host_id"))
                print("已删除无效的本地主机")
            except:
                pass
        
        # 创建一个新的
        print("正在创建新的 Agent Host...")
        try:
            local_host = manager.add_agent_host(
                name="本地主机",
                host_type="agent",
                description="用于本地调试的 Agent Host"
            )
            token = local_host.get("token")
            print(f"✅ 已创建新的 Agent Host")
        except Exception as e:
            print(f"❌ 创建失败: {e}")
            # 如果创建失败，尝试使用现有的有效 token
            for host in hosts:
                if host.get("host_type") == "agent" and host.get("token") and host.get("token") != "offline":
                    token = host.get("token")
                    print(f"使用现有 Host '{host.get('name')}' 的 Token")
                    break
            if not token or token == "offline":
                sys.exit(1)
    
    if not token:
        print("❌ 无法获取 Token")
        sys.exit(1)
    
    print(f"✅ Agent Token: {token}")
    print(f"\n使用方法:")
    print(f"  export AGENT_TOKEN={token}")
    print(f"  或在 VSCode launch.json 中使用此 token")
    
    return token

if __name__ == "__main__":
    main()

