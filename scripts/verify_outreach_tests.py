import pytest
import sys

sys.exit(pytest.main(["tests/unit/backend/test_outreach.py", "tests/unit/test_frontend_assets.py", "tests/unit/test_frontend_domain_config.py", "-q"]))
