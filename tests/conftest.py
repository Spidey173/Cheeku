import os
import sys
import glob

# Ensure repository root is on sys.path for pytest
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# If running outside active venv, automatically include project venv site-packages if present
venv_site_packages = glob.glob(os.path.join(ROOT_DIR, "venv", "lib", "python*", "site-packages"))
for sp in venv_site_packages:
    if sp not in sys.path and os.path.isdir(sp):
        sys.path.insert(0, sp)
