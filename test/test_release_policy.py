import tempfile
from pathlib import Path
import pytest
from backend.release_policy import validate_release, claim_release
from backend.app2docker_config import resolve_variables


def test_formal_release_policy_and_durable_claim(tmp_path):
    (tmp_path/'VERSION').write_text('py-7.3-20261102.1\n')
    policy={'enabled':True,'mainline':'py-7.3','platform':'jbm'}
    args=dict(source_dir=tmp_path,source_mode='git',branch='py-7.3',git_tag='py-7.3-20261102.1',commit='a'*40,images=['registry/jbm:py-7.3-20261102.1'])
    proof=validate_release(policy,**args)
    for change in [dict(source_mode='local'),dict(branch='fix/x'),dict(git_tag=None),dict(images=['registry/jbm:latest']),dict(commit='a'*7)]:
        with pytest.raises(ValueError):validate_release(policy,**{**args,**change})
    db=tmp_path/'claims.db'
    claim_release(db,proof,git_url='https://host/repo.git',task_id='first')
    claim_release(db,proof,git_url='https://host/repo.git',task_id='first')
    with pytest.raises(ValueError,match='已占用'):
        claim_release(db,proof,git_url='https://host/repo.git',task_id='second')
    assert resolve_variables('{full_commit}',{'commit':'b'*40})=='b'*40
