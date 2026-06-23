"""Default settings for the Nextcloud osf.io addon.

This package is installed (into site-packages), so per-deployment configuration
must NOT be edited inside the package. Instead the organizer overrides these in
the host osf.io Django settings (e.g. ``api/base/settings/local.py`` — the same
file where ``INSTALLED_APPS`` / ``ADDONS_FOLDER_CONFIGURABLE`` are set) using the
``NEXTCLOUD_*`` names below; this module reads them via ``getattr`` with a
built-in fallback.

Note: in the GRDM2 (angular-osf + GravyValet) architecture the storage *service*
configuration (endpoints / selectable hosts) lives in GravyValet
``ExternalStorageService`` rows, not here. ``DEFAULT_HOSTS`` is retained only for
backward compatibility and is largely vestigial.
"""
from django.conf import settings as _osf

DEFAULT_HOSTS = getattr(_osf, 'NEXTCLOUD_DEFAULT_HOSTS', [])
USE_SSL = getattr(_osf, 'NEXTCLOUD_USE_SSL', True)

# Max file size permitted by frontend in megabytes
MAX_UPLOAD_SIZE = getattr(_osf, 'NEXTCLOUD_MAX_UPLOAD_SIZE', 5 * 1024)
