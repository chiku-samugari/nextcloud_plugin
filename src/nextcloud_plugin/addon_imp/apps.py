from addon_toolkit.interfaces.foreign_addon_imp_config import ForeignAddonImpConfig

from .imp import NextcloudStorageImp


class NextcloudForeignAddonImpConfig(ForeignAddonImpConfig):
    name = "nextcloud_plugin.addon_imp"
    # Django defaults an app's label to the last path component ("addon_imp"),
    # which collides with every other "<pkg>.addon_imp" plugin. Set a unique
    # label. (GravyValet discovers imps via ForeignAddonImpConfig + addon_imp_name
    # / name, never the label, so any unique value is safe.)
    label = "nextcloud_addon_imp"
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
