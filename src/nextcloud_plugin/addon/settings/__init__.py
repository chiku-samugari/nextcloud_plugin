# Per-deployment configuration is read from the host osf.io Django settings
# (NEXTCLOUD_* names; see defaults.py), NOT from a local.py inside this
# installed package. Relative import keeps this rename-safe.
from .defaults import *  # noqa
