from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_revision_chain_is_complete_and_linear():
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "0027_calibration_reference"
    assert [revision.revision for revision in script.walk_revisions()][-1] == "0001"
