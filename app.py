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
    host = os.getenv("CAREERPROOF_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("CAREERPROOF_PORT", "7860")))
    uvicorn.run(app, host=host, port=port)
