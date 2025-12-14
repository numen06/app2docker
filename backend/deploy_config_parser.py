# backend/deploy_config_parser.py
"""
部署配置解析器
解析 deploy-config.yaml 格式，验证配置有效性，支持模板变量替换
"""
import yaml
import re
from typing import Dict, Any, List, Optional
from pathlib import Path


class DeployConfigParser:
    """部署配置解析器"""
    
    def __init__(self):
        """初始化解析器"""
        pass
    
    def parse_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """
        解析 YAML 配置文件
        
        Args:
            file_path: YAML 文件路径
        
        Returns:
            解析后的配置字典
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return self.parse_yaml_content(content)
    
    def parse_yaml_content(self, content: str) -> Dict[str, Any]:
        """
        解析 YAML 内容
        
        Args:
            content: YAML 内容字符串
        
        Returns:
            解析后的配置字典（标准化为新格式）
        """
        config = yaml.safe_load(content)
        
        if not isinstance(config, dict):
            raise ValueError("配置必须是字典格式")
        
        # 验证配置结构
        self._validate_config(config)
        
        # 标准化配置（迁移旧格式到新格式）
        config = self.normalize_config(config)
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]):
        """
        验证配置有效性（支持新旧两种格式）
        
        Args:
            config: 配置字典
        
        Raises:
            ValueError: 配置无效时抛出异常
        """
        # 检查必需字段
        if "app" not in config:
            raise ValueError("配置中缺少 'app' 字段")
        
        app_config = config.get("app", {})
        if "name" not in app_config:
            raise ValueError("app.name 是必需的")
        
        # 检查 targets
        if "targets" not in config:
            raise ValueError("配置中缺少 'targets' 字段")
        
        targets = config.get("targets", [])
        if not isinstance(targets, list) or len(targets) == 0:
            raise ValueError("targets 必须是非空列表")
        
        # 判断是新格式还是旧格式
        has_deploy_section = "deploy" in config
        
        if has_deploy_section:
            # 新格式：统一部署定义
            deploy_config = config.get("deploy", {})
            
            # 支持两种模式：单命令模式 或 多步骤模式
            if "steps" in deploy_config:
                # 多步骤模式
                steps = deploy_config.get("steps", [])
                if not isinstance(steps, list) or len(steps) == 0:
                    raise ValueError("deploy.steps 必须是非空列表")
                
                for i, step in enumerate(steps):
                    if not isinstance(step, dict):
                        raise ValueError(f"deploy.steps[{i}] 必须是字典格式")
                    if "name" not in step:
                        raise ValueError(f"deploy.steps[{i}].name 是必需的")
                    if "command" not in step:
                        raise ValueError(f"deploy.steps[{i}].command 是必需的")
            else:
                # 单命令模式（向后兼容）
                deploy_type = deploy_config.get("type")
                if deploy_type not in ["docker_run", "docker_compose"]:
                    raise ValueError("deploy.type 必须是 'docker_run' 或 'docker_compose'")
                
                if "command" not in deploy_config:
                    raise ValueError("deploy.command 是必需的")
                
                if deploy_type == "docker_compose":
                    if "compose_content" not in deploy_config:
                        raise ValueError("deploy.compose_content 是必需的（当 type=docker_compose 时）")
        
        # 验证每个 target
        for i, target in enumerate(targets):
            if not isinstance(target, dict):
                raise ValueError(f"targets[{i}] 必须是字典格式")
            
            if "name" not in target:
                raise ValueError(f"targets[{i}].name 是必需的")
            
            # 新格式：使用 host_type
            if "host_type" in target:
                host_type = target.get("host_type")
                if host_type not in ["agent", "portainer", "ssh"]:
                    raise ValueError(f"targets[{i}].host_type 必须是 'agent'、'portainer' 或 'ssh'")
                
                if "host_name" not in target:
                    raise ValueError(f"targets[{i}].host_name 是必需的（当使用 host_type 时）")
            else:
                # 旧格式：使用 mode
                mode = target.get("mode", "agent")
                if mode not in ["ssh", "agent"]:
                    raise ValueError(f"targets[{i}].mode 必须是 'ssh' 或 'agent'")
                
                # 验证 mode 对应的配置
                if mode == "agent":
                    if "agent" not in target:
                        raise ValueError(f"targets[{i}].agent 是必需的（当 mode=agent 时）")
                    
                    agent_config = target.get("agent", {})
                    if "name" not in agent_config:
                        raise ValueError(f"targets[{i}].agent.name 是必需的")
                elif mode == "ssh":
                    if "host" not in target:
                        raise ValueError(f"targets[{i}].host 是必需的（当 mode=ssh 时）")
                
                # 旧格式：验证 docker 配置
                if "docker" not in target:
                    raise ValueError(f"targets[{i}].docker 是必需的（旧格式）")
                
                docker_config = target.get("docker", {})
                if "image_template" not in docker_config and "command" not in docker_config:
                    raise ValueError(f"targets[{i}].docker 必须包含 'image_template' 或 'command'")
    
    def normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化配置：将旧格式迁移到新格式
        
        Args:
            config: 配置字典（可能是旧格式）
        
        Returns:
            标准化后的配置字典（新格式）
        """
        normalized = config.copy()
        
        # 如果已经是新格式，直接返回
        if "deploy" in normalized:
            return normalized
        
        # 旧格式迁移：从第一个target的docker配置提取部署信息
        targets = normalized.get("targets", [])
        if not targets:
            return normalized
        
        first_target = targets[0]
        docker_config = first_target.get("docker", {})
        
        # 确定部署类型
        deploy_mode = docker_config.get("deploy_mode", "docker_run")
        deploy_type = "docker_compose" if deploy_mode == "docker_compose" else "docker_run"
        
        # 构建统一的deploy配置
        deploy_config = {
            "type": deploy_type,
            "command": docker_config.get("command", "")
        }
        
        if deploy_type == "docker_compose":
            deploy_config["compose_content"] = docker_config.get("compose_content", "")
        
        normalized["deploy"] = deploy_config
        
        # 迁移targets格式
        normalized_targets = []
        for target in targets:
            normalized_target = {
                "name": target.get("name")
            }
            
            # 确定主机类型和名称
            mode = target.get("mode", "agent")
            if mode == "agent":
                agent_config = target.get("agent", {})
                agent_name = agent_config.get("name")
                # 需要查询主机类型（agent或portainer）
                # 这里先设为agent，执行时会根据实际主机类型调整
                normalized_target["host_type"] = "agent"
                normalized_target["host_name"] = agent_name
            elif mode == "ssh":
                normalized_target["host_type"] = "ssh"
                normalized_target["host_name"] = target.get("host")
            
            # 保留overrides（如果有）
            if "overrides" in target:
                normalized_target["overrides"] = target["overrides"]
            
            normalized_targets.append(normalized_target)
        
        normalized["targets"] = normalized_targets
        
        return normalized
    
    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        渲染模板字符串（支持 {{ variable }} 格式）
        
        Args:
            template: 模板字符串
            context: 变量上下文
        
        Returns:
            渲染后的字符串
        """
        result = template
        
        # 查找所有模板变量 {{ variable }}
        pattern = r'\{\{\s*(\w+)\s*\}\}'
        matches = re.findall(pattern, template)
        
        for var_name in matches:
            if var_name in context:
                value = str(context[var_name])
                placeholder = f"{{{{ {var_name} }}}}"
                result = result.replace(placeholder, value)
            else:
                # 如果变量不存在，保留原样（或可以抛出异常）
                pass
        
        return result
    
    def build_deploy_context(
        self,
        config: Dict[str, Any],
        registry: Optional[str] = None,
        tag: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建部署上下文（模板变量）
        
        Args:
            config: 部署配置
            registry: 镜像仓库地址（可选）
            tag: 镜像标签（可选）
            task_id: 任务ID（可选）
        
        Returns:
            上下文字典
        """
        app_config = config.get("app", {})
        
        context = {
            "app": {
                "name": app_config.get("name", ""),
                "repo": app_config.get("repo", ""),
            },
            "registry": registry or "docker.io",
            "tag": tag or "latest",
        }
        
        if task_id:
            context["task_id"] = task_id
        
        # 支持嵌套访问，如 {{ app.name }}
        # 将 app.name 展开为 app_name
        context["app_name"] = app_config.get("name", "")
        context["app_repo"] = app_config.get("repo", "")
        
        return context
    
    def render_target_config(
        self,
        target: Dict[str, Any],
        context: Dict[str, Any],
        deploy_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        渲染目标配置（替换模板变量）
        支持新旧两种格式
        
        Args:
            target: 目标配置
            context: 模板变量上下文
            deploy_config: 部署配置（新格式）
        
        Returns:
            渲染后的目标配置
        """
        rendered = target.copy()
        
        # 新格式：渲染deploy配置
        if deploy_config:
            rendered_deploy = deploy_config.copy()
            
            # 渲染command
            if "command" in rendered_deploy:
                rendered_deploy["command"] = self.render_template(
                    rendered_deploy["command"],
                    context
                )
            
            # 渲染compose_content
            if "compose_content" in rendered_deploy:
                rendered_deploy["compose_content"] = self.render_template(
                    rendered_deploy["compose_content"],
                    context
                )
            
            rendered["deploy"] = rendered_deploy
        
        # 旧格式：渲染 docker 配置（向后兼容）
        if "docker" in target:
            docker_config = target.get("docker", {}).copy()
            
            # 渲染 image_template
            if "image_template" in docker_config:
                docker_config["image_template"] = self.render_template(
                    docker_config["image_template"],
                    context
                )
            
            # 渲染 container_name
            if "container_name" in docker_config:
                docker_config["container_name"] = self.render_template(
                    docker_config["container_name"],
                    context
                )
            
            # 渲染环境变量
            if "env" in docker_config:
                env_vars = []
                for env_var in docker_config["env"]:
                    rendered_env = self.render_template(env_var, context)
                    env_vars.append(rendered_env)
                docker_config["env"] = env_vars
            
            rendered["docker"] = docker_config
        
        return rendered
    
    def get_deploy_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取部署配置（统一格式）
        
        Args:
            config: 配置字典
        
        Returns:
            部署配置字典
        """
        # 新格式：直接返回deploy配置
        if "deploy" in config:
            return config["deploy"]
        
        # 旧格式：从第一个target的docker配置构建
        targets = config.get("targets", [])
        if not targets:
            return {}
        
        first_target = targets[0]
        docker_config = first_target.get("docker", {})
        
        deploy_mode = docker_config.get("deploy_mode", "docker_run")
        deploy_type = "docker_compose" if deploy_mode == "docker_compose" else "docker_run"
        
        deploy_config = {
            "type": deploy_type,
            "command": docker_config.get("command", "")
        }
        
        if deploy_type == "docker_compose":
            deploy_config["compose_content"] = docker_config.get("compose_content", "")
        
        return deploy_config
    
    def get_targets_by_mode(
        self,
        config: Dict[str, Any],
        mode: str
    ) -> List[Dict[str, Any]]:
        """
        根据模式获取目标列表
        
        Args:
            config: 部署配置
            mode: 模式（"ssh" 或 "agent"）
        
        Returns:
            目标列表
        """
        targets = config.get("targets", [])
        return [t for t in targets if t.get("mode") == mode]
    
    def get_agent_targets(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取所有 Agent 模式的目标
        
        Args:
            config: 部署配置
        
        Returns:
            Agent 目标列表
        """
        return self.get_targets_by_mode(config, "agent")
    
    def get_ssh_targets(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取所有 SSH 模式的目标
        
        Args:
            config: 部署配置
        
        Returns:
            SSH 目标列表
        """
        return self.get_targets_by_mode(config, "ssh")

