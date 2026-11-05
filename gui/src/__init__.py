import os

# Developer tool for copy reviews (copyhints.py); does nothing unless TORQUIO_COPY_HINTS or TORQUIO_COPY_FAKE is set
if os.environ.get("TORQUIO_COPY_HINTS") == "1":
    from . import copyhints
    copyhints.install()
elif os.environ.get("TORQUIO_COPY_FAKE") == "1":
    from . import copyfake
    copyfake.install()
