# backend/team_deletion.py
"""团队级联删除（含业务数据）"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.database import DEFAULT_TEAM_NAME, DEFAULT_TEAM_SLUG
from backend.models import (
    AgentHost,
    DeployConfig,
    DeployConfigPermission,
    DockerRegistry,
    ExportTask,
    GitSource,
    GitSourcePermission,
    Host,
    HostGroup,
    HostGroupPermission,
    HostPermission,
    OperationLog,
    Pipeline,
    PipelineGroup,
    PipelineGroupPermission,
    PipelinePermission,
    PipelineTaskHistory,
    RegistryPermission,
    ResourcePackage,
    ResourcePackagePermission,
    Task,
    TaskLog,
    Team,
    TemplatePermission,
    TemplateRecord,
)


def is_protected_default_team(team: Team) -> bool:
    return team.name == DEFAULT_TEAM_NAME or team.slug == DEFAULT_TEAM_SLUG


def assert_team_deletable(team: Team) -> None:
    if is_protected_default_team(team):
        raise HTTPException(
            status_code=400,
            detail=f"不能删除系统保留团队「{DEFAULT_TEAM_NAME}」",
        )


def delete_team_cascade(db: Session, team_id: str) -> None:
    """删除团队及其全部关联业务数据。"""
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    assert_team_deletable(team)

    pipeline_ids = [
        r[0]
        for r in db.query(Pipeline.pipeline_id)
        .filter(Pipeline.team_id == team_id)
        .all()
    ]
    task_ids_by_team = [
        r[0] for r in db.query(Task.task_id).filter(Task.team_id == team_id).all()
    ]
    task_ids_by_pipeline = []
    if pipeline_ids:
        task_ids_by_pipeline = [
            r[0]
            for r in db.query(Task.task_id)
            .filter(Task.pipeline_id.in_(pipeline_ids))
            .all()
        ]
    task_ids = list({*task_ids_by_team, *task_ids_by_pipeline})

    group_ids = [
        r[0]
        for r in db.query(PipelineGroup.group_id)
        .filter(PipelineGroup.team_id == team_id)
        .all()
    ]
    host_group_ids = [
        r[0]
        for r in db.query(HostGroup.group_id).filter(HostGroup.team_id == team_id).all()
    ]

    agent_host_ids = [
        r[0]
        for r in db.query(AgentHost.host_id)
        .filter(AgentHost.team_id == team_id)
        .all()
    ]
    host_ids = [r[0] for r in db.query(Host.host_id).filter(Host.team_id == team_id).all()]
    deploy_config_ids = [
        r[0]
        for r in db.query(DeployConfig.config_id)
        .filter(DeployConfig.team_id == team_id)
        .all()
    ]
    git_source_ids = [
        r[0]
        for r in db.query(GitSource.source_id).filter(GitSource.team_id == team_id).all()
    ]
    package_ids = [
        r[0]
        for r in db.query(ResourcePackage.package_id)
        .filter(ResourcePackage.team_id == team_id)
        .all()
    ]
    registry_ids = [
        r[0]
        for r in db.query(DockerRegistry.registry_id)
        .filter(DockerRegistry.team_id == team_id)
        .all()
    ]
    template_ids = [
        r[0]
        for r in db.query(TemplateRecord.template_id)
        .filter(TemplateRecord.team_id == team_id)
        .all()
    ]

    if pipeline_ids:
        db.query(Pipeline).filter(Pipeline.team_id == team_id).update(
            {Pipeline.current_task_id: None},
            synchronize_session=False,
        )

    if pipeline_ids:
        db.query(PipelinePermission).filter(
            PipelinePermission.pipeline_id.in_(pipeline_ids)
        ).delete(synchronize_session=False)
    if group_ids:
        db.query(PipelineGroupPermission).filter(
            PipelineGroupPermission.group_id.in_(group_ids)
        ).delete(synchronize_session=False)
    if pipeline_ids:
        db.query(PipelineTaskHistory).filter(
            PipelineTaskHistory.pipeline_id.in_(pipeline_ids)
        ).delete(synchronize_session=False)

    if task_ids:
        db.query(TaskLog).filter(TaskLog.task_id.in_(task_ids)).delete(
            synchronize_session=False
        )
        db.query(PipelineTaskHistory).filter(
            PipelineTaskHistory.task_id.in_(task_ids)
        ).delete(synchronize_session=False)
        db.query(Task).filter(Task.task_id.in_(task_ids)).delete(synchronize_session=False)

    if pipeline_ids:
        db.query(Pipeline).filter(Pipeline.team_id == team_id).delete(
            synchronize_session=False
        )

    if agent_host_ids:
        db.query(HostPermission).filter(HostPermission.host_id.in_(agent_host_ids)).delete(
            synchronize_session=False
        )
    if host_group_ids:
        db.query(HostGroupPermission).filter(
            HostGroupPermission.group_id.in_(host_group_ids)
        ).delete(synchronize_session=False)
    if agent_host_ids:
        db.query(AgentHost).filter(AgentHost.team_id == team_id).delete(
            synchronize_session=False
        )
    if host_ids:
        db.query(Host).filter(Host.team_id == team_id).delete(synchronize_session=False)

    if deploy_config_ids:
        db.query(DeployConfigPermission).filter(
            DeployConfigPermission.config_id.in_(deploy_config_ids)
        ).delete(synchronize_session=False)
        db.query(DeployConfig).filter(DeployConfig.team_id == team_id).delete(
            synchronize_session=False
        )

    if git_source_ids:
        db.query(GitSourcePermission).filter(
            GitSourcePermission.source_id.in_(git_source_ids)
        ).delete(synchronize_session=False)
        db.query(GitSource).filter(GitSource.team_id == team_id).delete(
            synchronize_session=False
        )

    if package_ids:
        db.query(ResourcePackagePermission).filter(
            ResourcePackagePermission.package_id.in_(package_ids)
        ).delete(synchronize_session=False)
        db.query(ResourcePackage).filter(ResourcePackage.team_id == team_id).delete(
            synchronize_session=False
        )

    if registry_ids:
        db.query(RegistryPermission).filter(
            RegistryPermission.registry_id.in_(registry_ids)
        ).delete(synchronize_session=False)
        db.query(DockerRegistry).filter(DockerRegistry.team_id == team_id).delete(
            synchronize_session=False
        )

    if template_ids:
        db.query(TemplatePermission).filter(
            TemplatePermission.template_id.in_(template_ids)
        ).delete(synchronize_session=False)
        db.query(TemplateRecord).filter(TemplateRecord.team_id == team_id).delete(
            synchronize_session=False
        )

    db.query(ExportTask).filter(ExportTask.team_id == team_id).delete(
        synchronize_session=False
    )
    db.query(OperationLog).filter(OperationLog.team_id == team_id).delete(
        synchronize_session=False
    )
    db.query(PipelineGroup).filter(PipelineGroup.team_id == team_id).delete(
        synchronize_session=False
    )
    db.query(HostGroup).filter(HostGroup.team_id == team_id).delete(
        synchronize_session=False
    )

    db.delete(team)
    db.commit()
