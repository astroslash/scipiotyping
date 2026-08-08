from __future__ import annotations

import os

from . import create_app


app = create_app()
app.run(
    host=os.environ.get("SCIPIO_HOST", "127.0.0.1"),
    port=int(os.environ.get("SCIPIO_PORT", "5000")),
    debug=False,
)

