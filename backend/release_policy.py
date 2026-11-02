"""Opt-in immutable Git releases declared in .app2docker.yaml.

Claims live in the existing durable App2Docker database. Failed builds retain
their claim: retries require a new release number, never an overwritten image.
"""
from datetime import datetime
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit, urlunsplit


def validate_release(policy, *, source_dir, source_mode, branch, git_tag, commit, images):
    if not policy or not policy.get('enabled'):
        return None
    mainline = policy['mainline']
    if source_mode != 'git' or branch not in (mainline, git_tag) or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('正式发布只允许已冻结的 Git 主线完整提交：' + mainline)
    version_path = (Path(source_dir) / policy.get('version_file', 'VERSION')).resolve()
    if not version_path.is_relative_to(Path(source_dir).resolve()):
        raise ValueError('VERSION 路径不能超出仓库')
    version = version_path.read_text(encoding='utf-8').strip()
    match = re.fullmatch(re.escape(mainline) + r'-(\d{8})\.([1-9][0-9]*)', version)
    if not match:
        raise ValueError('正式版本必须为 Git主线-YYYYMMDD.N，序号从1递增')
    datetime.strptime(match.group(1), '%Y%m%d')
    if policy.get('timezone', 'Asia/Shanghai') != 'Asia/Shanghai':
        raise ValueError('发布日期时区必须为 Asia/Shanghai')
    if git_tag != version:
        raise ValueError('必须使用与 VERSION 同名的冻结 Git 标签构建')
    if not images or any(image.rsplit(':', 1)[-1] != version or '@' in image for image in images):
        raise ValueError('所有输出镜像必须使用 VERSION 中的同一正式版本')
    return {'platform': policy['platform'], 'mainline': mainline, 'version': version,
            'date': match.group(1), 'sequence': int(match.group(2)), 'commit': commit,
            'images': images, 'immutable': True}


def claim_release(db_file, proof, *, git_url, task_id):
    if not proof:
        return
    parsed = urlsplit(git_url)
    repository = urlunsplit((parsed.scheme, parsed.hostname or '', parsed.path.rstrip('/'), '', ''))
    with sqlite3.connect(str(db_file), timeout=30) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('''CREATE TABLE IF NOT EXISTS formal_release_claims (
            image TEXT PRIMARY KEY, repository TEXT NOT NULL, platform TEXT NOT NULL,
            mainline TEXT NOT NULL, version TEXT NOT NULL, release_date TEXT NOT NULL,
            sequence INTEGER NOT NULL, source_commit TEXT NOT NULL, task_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        for image in proof['images']:
            existing = db.execute('SELECT task_id,source_commit FROM formal_release_claims WHERE image=?', (image,)).fetchone()
            if existing:
                if existing != (task_id, proof['commit']):
                    raise ValueError('正式镜像版本已占用，失败构建也不能复用：' + image)
                continue
            highest = db.execute('''SELECT MAX(sequence) FROM formal_release_claims
                WHERE repository=? AND platform=? AND mainline=? AND release_date=?''',
                (repository, proof['platform'], proof['mainline'], proof['date'])).fetchone()[0]
            if highest is not None and proof['sequence'] < highest:
                raise ValueError('发布日期内序号必须递增，不能回用较小序号')
            db.execute('INSERT INTO formal_release_claims(image,repository,platform,mainline,version,release_date,sequence,source_commit,task_id) VALUES(?,?,?,?,?,?,?,?,?)',
                (image, repository, proof['platform'], proof['mainline'], proof['version'], proof['date'], proof['sequence'], proof['commit'], task_id))
