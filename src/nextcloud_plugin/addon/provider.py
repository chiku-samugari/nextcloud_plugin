# -*- coding: utf-8 -*-
"""Nextcloud osf.io auth provider.

Kept in its own module (mirroring ``s3compat_plugin/addon/provider.py`` and the
RDM developer-guide file structure); ``models.py`` imports ``NextcloudProvider``
from here. Nextcloud authenticates with host/username/password, so this is a
``BasicAuthProviderMixin`` subclass rather than an OAuth ``ExternalProvider``.
"""
from osf.models.external import BasicAuthProviderMixin


class NextcloudProvider(BasicAuthProviderMixin):
    """An alternative to `ExternalProvider` not tied to OAuth."""

    name = 'Nextcloud'
    short_name = 'nextcloud'

    def __init__(self, account=None, host=None, username=None, password=None):
        if username:
            username = username.lower()
        return super().__init__(account=account, host=host, username=username, password=password)

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )
