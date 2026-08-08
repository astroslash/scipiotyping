from __future__ import annotations

import os
import threading
import webbrowser

from waitress import serve

from . import create_app


def main() -> None:
    host = os.environ.get("SCIPIO_HOST", "127.0.0.1")
    port = int(os.environ.get("SCIPIO_PORT", "5000"))
    url = f"http://{host}:{port}"
    if os.environ.get("SCIPIO_NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"ScipioTyping is ready at {url}")
    print("Press Ctrl+C to stop it.")
    serve(create_app(), host=host, port=port, threads=4)


if __name__ == "__main__":
    main()

