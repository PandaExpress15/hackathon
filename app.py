from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import uvicorn

from careerproof.webapp import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("CAREERPROOF_HOST", "127.0.0.1"), port=int(os.getenv("CAREERPROOF_PORT", "7860")))
