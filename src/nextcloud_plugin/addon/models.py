# -*- coding: utf-8 -*-
"""Nextcloud osf.io addon models.

Ported from RDM-osf.io ``addons/nextcloud/models.py``. The only structural
change from the RDM original is the file-node trio: they are now explicit
**proxy** models carrying ``TypedModelRejoinMixin`` + ``db_owner='osf'`` +
``Meta.app_label='addons_nextcloud'`` so that (a) migrations stay in THIS
package and (b) the proxy classes rejoin TypedModel's registry at ready().
See ``nextcloud_plugin.addon.typedmodel_workaround`` and the s3compat_plugin
reference for why this dance is needed.
"""
import logging

from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from framework.auth import Auth
from osf.models.files import File, Folder, BaseFileNode
from owncloud import Client as NextcloudClient
from addons.base import exceptions
from nextcloud_plugin.addon import settings
from nextcloud_plugin.addon.serializer import NextcloudSerializer
from nextcloud_plugin.addon.settings import DEFAULT_HOSTS, USE_SSL
from osf.models.external import BasicAuthProviderMixin
from website.util import api_v2_url

from .typedmodel_workaround import TypedModelRejoinMixin

logger = logging.getLogger(__name__)


class NextcloudFileNode(TypedModelRejoinMixin, BaseFileNode):
    """Base file node for Nextcloud storage.

    Declared as a proxy model with an explicit ``app_label`` so migrations are
    generated in this addon's ``migrations`` directory rather than in osf.io.
    TypedModel deliberately stops managing classes that are explicitly declared
    proxy; ``TypedModelRejoinMixin`` re-registers this class into TypedModel's
    registry (keyed by ``db_owner`` instead of ``app_label``).
    """
    _provider = 'nextcloud'
    db_owner = 'osf'

    class Meta:
        proxy = True
        app_label = 'addons_nextcloud'


class NextcloudFolder(NextcloudFileNode, Folder):
    class Meta:
        proxy = True


class NextcloudFile(NextcloudFileNode, File):
    class Meta:
        proxy = True


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


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = NextcloudProvider
    serializer = NextcloudSerializer

    def to_json(self, user):
        ret = super().to_json(user)
        ret['hosts'] = DEFAULT_HOSTS
        return ret


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = NextcloudProvider
    serializer = NextcloudSerializer

    folder_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    _api = None

    @property
    def api(self):
        if self._api is None:
            self._api = NextcloudProvider(self.external_account)
        return self._api

    @property
    def folder_path(self):
        return self.folder_id

    @property
    def folder_name(self):
        return self.folder_id

    def set_folder(self, folder, auth=None):
        if folder == '/ (Full Nextcloud)':
            folder = '/'
        self.folder_id = folder
        self.save()
        self.nodelogger.log(action='folder_selected', save=True)

    def fetch_folder_name(self):
        if self.folder_id == '/':
            return '/ (Full Nextcloud)'
        return self.folder_id.strip('/').split('/')[-1]

    def clear_settings(self):
        self.folder_id = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        if add_log:
            self.nodelogger.log(action='node_deauthorized')
        self.clear_auth()  # Also performs a .save()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        provider = NextcloudProvider(self.external_account)
        return {
            'host': provider.host,
            'username': provider.username,
            'password': provider.password
        }

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Nextcloud is not configured')
        return {
            'folder': self.folder_id,
            'verify_ssl': USE_SSL
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file',
                                     path=metadata['path'], provider='nextcloud')
        self.owner.add_log(
            'nextcloud_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder': self.folder_id,
                'path': metadata['materialized'].lstrip('/'),
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def after_delete(self, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()

    def get_folders(self, **kwargs):
        path = kwargs.get('path')
        if path is None:
            return [{
                'addon': 'nextcloud',
                'path': '/',
                'kind': 'folder',
                'id': '/',
                'name': '/ (Full Nextcloud)',
                'urls': {
                    'folders': api_v2_url('nodes/{}/addons/nextcloud/folders/'.format(self.owner._id),
                        params={
                            'path': '/',
                    })
                }
            }]

        provider = NextcloudProvider(account=self.external_account)

        c = NextcloudClient(provider.host, verify_certs=settings.USE_SSL)
        c.login(provider.username, provider.password)

        ret = []
        for item in c.list(path):
            if item.file_type == 'dir':
                ret.append({
                    'addon': 'nextcloud',
                    'path': item.path,
                    'kind': 'folder',
                    'id': item.path,
                    'name': item.path.strip('/').split('/')[-1],
                    'urls': {
                        'folders': api_v2_url('nodes/{}/addons/nextcloud/folders/'.format(self.owner._id),
                            params={
                                'path': item.path,
                        })

                    }
                })

        return ret
