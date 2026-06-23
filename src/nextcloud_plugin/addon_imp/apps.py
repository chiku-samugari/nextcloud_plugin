from addon_toolkit.interfaces.foreign_addon_imp_config import ForeignAddonImpConfig

from .imp import NextcloudStorageImp


class NextcloudForeignAddonImpConfig(ForeignAddonImpConfig):
    name = "nextcloud_plugin.addon_imp"
    verbose_name = "Nextcloud"
    default = True

    @property
    def imp(self):
        return NextcloudStorageImp

    @property
    def addon_imp_name(self):
        # MUST be unique across the GravyValet installation and must not
        # collide with addon_service.common.known_imps.KnownAddonImps.
        return "NEXTCLOUD"
