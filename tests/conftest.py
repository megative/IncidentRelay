import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
TEST_CONFIG = ROOT_DIR / "tests" / "incidentrelay.test.conf"

os.environ.setdefault("INCEDENTRELAY_CONFIG_FILE", str(TEST_CONFIG))

(ROOT_DIR / "tests" / ".tmp").mkdir(parents=True, exist_ok=True)
(ROOT_DIR / "logs").mkdir(parents=True, exist_ok=True)
