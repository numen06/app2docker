"""解析仓库根目录 .app2docker.yaml 配置文件（文件名体现 profile）。"""
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote, urlparse, urlunparse

import yaml


def safe_profile_filename(name: str) -> str:
    """将 profile/分支/tag 名转为安全文件名片段。"""
    if not name:
        return ""
    return re.sub(r"[^\w.\-]+", "-", name.strip())


def resolve_profile(
    profile: Optional[str] = None,
    branch: Optional[str] = None,
    tag_name: Optional[str] = None,
) -> str:
    """推导最终 profile 名。"""
    if profile:
        return profile.strip()
    if tag_name:
        return tag_name.strip()
    if branch:
        return branch.strip()
    return "default"


def config_filename_for_profile(profile: str) -> str:
    if profile == "default":
        return ".app2docker.yaml"
    return f".app2docker-{safe_profile_filename(profile)}.yaml"


def find_config_file(source_dir: str, profile: str) -> Tuple[Optional[str], str]:
    """
    根据 profile 查找配置文件。
    返回 (文件路径, 实际使用的 profile 名)。
    """
    if profile == "default":
        path = os.path.join(source_dir, ".app2docker.yaml")
        return (path if os.path.exists(path) else None, "default")

    safe_name = safe_profile_filename(profile)
    profile_path = os.path.join(source_dir, f".app2docker-{safe_name}.yaml")
    if os.path.exists(profile_path):
        return profile_path, profile

    default_path = os.path.join(source_dir, ".app2docker.yaml")
    if os.path.exists(default_path):
        return default_path, "default"

    return None, profile


def parse_config(yaml_content: str) -> dict:
    """解析 yaml 内容为字典。"""
    data = yaml.safe_load(yaml_content) or {}
    if not isinstance(data, dict):
        raise ValueError("配置文件格式无效，根节点必须是对象")
    return data


def resolve_variables(value: Any, context: dict) -> Any:
    """替换字符串中的变量占位符。"""
    if not isinstance(value, str):
        return value

    result = value
    replacements = {
        "{branch}": str(context.get("branch") or ""),
        "{profile}": str(context.get("profile") or ""),
        "{date}": datetime.now().strftime("%Y%m%d"),
        "{commit}": str(context.get("commit") or "")[:7],
        "{full_commit}": str(context.get("commit") or ""),
        "{timestamp}": str(int(datetime.now().timestamp())),
    }
    for key, repl in replacements.items():
        result = result.replace(key, repl)
    return result


def _build_full_image_name(image_cfg: dict) -> str:
    name = (image_cfg.get("name") or "").strip()
    prefix = (image_cfg.get("prefix") or "").strip().rstrip("/")
    if prefix and name:
        return f"{prefix}/{name}"
    return name or prefix


def config_to_build_params(config: dict, context: dict) -> dict:
    """将配置文件转换为构建参数字典。"""
    build_cfg = config.get("build") or {}
    image_cfg = config.get("image") or {}
    git_cfg = config.get("git") or {}

    image_tag = resolve_variables(image_cfg.get("tag") or "latest", context)
    full_image = _build_full_image_name(image_cfg)

    selected_services = _extract_services(config)
    return {
        "project_type": build_cfg.get("project_type") or "jar",
        "template": build_cfg.get("template") or "",
        "dockerfile_name": build_cfg.get("dockerfile_name") or "Dockerfile",
        "use_project_dockerfile": build_cfg.get("use_project_dockerfile", True),
        "sub_path": build_cfg.get("sub_path"),
        "build_args": _extract_build_args(build_cfg, context),
        "platforms": _extract_platforms(build_cfg),
        "image_name": full_image or "myapp/demo",
        "tag": image_tag,
        "should_push": bool(image_cfg.get("push", False)),
        "template_params": config.get("template_params") or {},
        "branch": git_cfg.get("branch"),
        "selected_services": selected_services,
        "service_push_config": _extract_service_push_config(config, context),
        "service_template_params": config.get("service_template_params") or {},
        "push_mode": (
            config.get("push_mode")
            or ("multi" if selected_services and len(selected_services) > 1 else "single")
        ),
        "resource_package_ids": _extract_resource_package_configs(config),
    }


def _extract_build_args(build_cfg: dict, context: dict) -> dict:
    """提取 Docker 构建参数，并解析 profile/分支等变量。"""
    raw = build_cfg.get("build_args") or {}
    if not isinstance(raw, dict):
        raise ValueError("build.build_args 必须是对象")

    result = {}
    for key, value in raw.items():
        if key is None or value is None:
            continue
        resolved = resolve_variables(value, context)
        if isinstance(resolved, bool):
            resolved = "true" if resolved else "false"
        elif not isinstance(resolved, str):
            resolved = str(resolved)
        result[str(key)] = resolved
    return result


def _extract_platforms(build_cfg: dict) -> list[str]:
    """提取并校验 Docker 目标平台。"""
    raw = build_cfg.get("platforms") or []
    if isinstance(raw, str):
        raw = [item.strip() for item in raw.split(",")]
    if not isinstance(raw, list):
        raise ValueError("build.platforms 必须是数组或逗号分隔字符串")
    result = []
    for item in raw:
        value = str(item or "").strip()
        if value and value not in result:
            result.append(value)
    return result


def _extract_resource_package_configs(config: dict) -> Optional[list]:
    raw = (
        config.get("resource_package_configs")
        or config.get("resource_package_ids")
        or config.get("resource_packages")
    )
    if raw is None:
        build_cfg = config.get("build") or {}
        raw = (
            build_cfg.get("resource_package_configs")
            or build_cfg.get("resource_package_ids")
            or build_cfg.get("resource_packages")
        )
    if not raw:
        return None
    if isinstance(raw, list):
        result = []
        for item in raw:
            if isinstance(item, dict):
                package_id = str(item.get("package_id") or item.get("id") or "").strip()
                if not package_id:
                    continue
                target_path = (
                    item.get("target_path")
                    or item.get("target_dir")
                    or item.get("path")
                    or "resources"
                )
                result.append(
                    {
                        "package_id": package_id,
                        "target_path": str(target_path).strip() or "resources",
                    }
                )
            elif isinstance(item, str) and item.strip():
                result.append({"package_id": item.strip(), "target_path": "resources"})
        return result or None
    return None


def _extract_services(config: dict) -> Optional[list]:
    services = config.get("services")
    if not services:
        return None
    names = []
    for item in services:
        if isinstance(item, dict) and item.get("name"):
            names.append(item["name"])
        elif isinstance(item, str):
            names.append(item)
    return names or None


def _extract_service_push_config(config: dict, context: dict) -> Optional[dict]:
    services = config.get("services")
    if not services:
        return None

    result = {}
    image_cfg = config.get("image") or {}
    default_prefix = (image_cfg.get("prefix") or "").strip().rstrip("/")
    default_tag = resolve_variables(image_cfg.get("tag") or "latest", context)

    for item in services:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        name = item["name"]
        image_name = item.get("image_name") or name
        if default_prefix and "/" not in image_name:
            image_name = f"{default_prefix}/{image_name}"
        tag = resolve_variables(item.get("tag") or default_tag, context)
        result[name] = {
            "push": bool(item.get("push", image_cfg.get("push", False))),
            "imageName": image_name,
            "tag": tag,
            "registry": item.get("registry", ""),
        }
    return result or None


def merge_with_overrides(config_params: dict, overrides: dict) -> dict:
    """用户请求参数覆盖配置文件（仅覆盖非空值）。"""
    merged = dict(config_params)
    field_map = {
        "project_type": "project_type",
        "template": "template",
        "dockerfile_name": "dockerfile_name",
        "use_project_dockerfile": "use_project_dockerfile",
        "sub_path": "sub_path",
        "image_name": "image_name",
        "imagename": "image_name",
        "tag": "tag",
        "push": "should_push",
        "should_push": "should_push",
        "branch": "branch",
        "template_params": "template_params",
        "build_args": "build_args",
    }

    for src, dst in field_map.items():
        val = overrides.get(src)
        if val is None:
            continue
        if isinstance(val, str) and val.strip() == "":
            continue
        if dst == "should_push":
            if isinstance(val, bool):
                merged[dst] = val
            elif isinstance(val, str):
                merged[dst] = val.lower() in ("on", "true", "1", "yes")
            continue
        merged[dst] = val

    return merged


def _embed_git_auth(git_url: str, username: str, password: str) -> str:
    if not (
        git_url.startswith("https://")
        and username
        and password
    ):
        return git_url
    parsed = urlparse(git_url)
    auth_url = urlunparse(
        (
            parsed.scheme,
            f"{quote(username, safe='')}:{quote(password, safe='')}@{parsed.netloc}",
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
    return auth_url


def _clone_shallow(
    git_url: str,
    target_dir: str,
    branch: Optional[str],
    git_config: Optional[dict],
) -> bool:
    git_config = git_config or {}
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd.extend(["-b", branch])

    clone_url = git_url
    if git_config.get("username") and git_config.get("password"):
        clone_url = _embed_git_auth(
            git_url, git_config["username"], git_config["password"]
        )

    cmd.extend([clone_url, target_dir])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return result.returncode == 0


def peek_profile_config(
    git_url: str,
    profile: str = "default",
    branch: Optional[str] = None,
    git_config: Optional[dict] = None,
) -> Tuple[Optional[dict], Optional[str]]:
    """
    浅克隆仓库并读取 profile 对应配置文件（用于确定默认分支等）。
    返回 (配置字典, 配置文件名)。
    """
    temp_root = tempfile.mkdtemp(prefix="app2docker_peek_")
    try:
        clone_dir = os.path.join(temp_root, "repo")
        if not _clone_shallow(git_url, clone_dir, branch, git_config):
            return None, None

        config_path, _ = find_config_file(clone_dir, profile)
        if not config_path:
            return None, None

        with open(config_path, "r", encoding="utf-8") as f:
            return parse_config(f.read()), os.path.basename(config_path)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def inspect_repository_config(
    git_url: str,
    profile: Optional[str] = None,
    branch: Optional[str] = None,
    tag_name: Optional[str] = None,
    git_config: Optional[dict] = None,
) -> dict:
    """克隆指定 Git 引用并返回可用于流水线的仓库配置快照。"""
    requested_profile = resolve_profile(profile, branch=branch, tag_name=tag_name)
    checkout_ref = tag_name or branch
    temp_root = tempfile.mkdtemp(prefix="app2docker_inspect_")
    try:
        clone_dir = os.path.join(temp_root, "repo")
        if not _clone_shallow(git_url, clone_dir, checkout_ref, git_config):
            raise RuntimeError("Git 仓库克隆失败，无法检测 .app2docker 配置")

        commit_hash = ""
        result = subprocess.run(
            ["git", "-C", clone_dir, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            commit_hash = result.stdout.strip()

        config_path, used_profile = find_config_file(clone_dir, requested_profile)
        if not config_path:
            return {
                "found": False,
                "requested_profile": requested_profile,
                "used_profile": None,
                "config_source": None,
                "commit": commit_hash,
                "build_params": {},
                "warnings": [
                    f"未找到 {config_filename_for_profile(requested_profile)}"
                    + (
                        " 或 .app2docker.yaml"
                        if requested_profile != "default"
                        else ""
                    )
                ],
            }

        with open(config_path, "r", encoding="utf-8") as f:
            config = parse_config(f.read())

        context = {
            "branch": branch or "",
            "profile": used_profile,
            "commit": commit_hash,
        }
        params = config_to_build_params(config, context)
        warnings = []
        if params.get("resource_package_ids"):
            warnings.append(
                "仓库配置中的资源包不会自动导入流水线；请在平台中按团队权限配置"
            )

        return {
            "found": True,
            "requested_profile": requested_profile,
            "used_profile": used_profile,
            "config_source": os.path.basename(config_path),
            "commit": commit_hash,
            "build_params": params,
            "warnings": warnings,
        }
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
