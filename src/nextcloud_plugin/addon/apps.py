import os
from addons.base.apps import BaseAddonAppConfig, generic_root_folder
from .settings import MAX_UPLOAD_SIZE

nextcloud_root_folder = generic_root_folder('nextcloud')

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)


class NextcloudAddonAppConfig(BaseAddonAppConfig):

    default = True
    name = 'nextcloud_plugin.addon'
    label = 'addons_nextcloud'
    full_name = 'Nextcloud'
    short_name = 'nextcloud'
    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']
    has_hgrid_files = True
    max_file_size = MAX_UPLOAD_SIZE
    node_settings_template = os.path.join(TEMPLATE_PATH, 'nextcloud_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'nextcloud_user_settings.mako')

    def ready(self):
        super().ready()

        # Import here to avoid AppRegistryNotReady errors.
        from .models import NextcloudFileNode, NextcloudFile, NextcloudFolder
        from .typedmodel_workaround import rejoin_models

        # The file/folder models are declared as proxy with an explicit
        # app_label (so migrations stay in this addon), which makes
        # TypedModel stop managing them. rejoin_models puts them back under
        # TypedModel's control. See typedmodel_workaround for details.
        rejoin_models(NextcloudFileNode, NextcloudFile, NextcloudFolder)

    @property
    def get_hgrid_data(self):
        return nextcloud_root_folder

    actions = ()

    @property
    def routes(self):
        from . import routes
        return [routes.api_routes]

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
