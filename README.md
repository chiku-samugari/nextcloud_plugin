# `nextcloud_plugin`

Nextcloud storage addon for the **upstream** OSF stack, packaged as a single
standalone plugin that bundles the full triplet:

| Piece | Package | What it is |
|-------|---------|------------|
| osf.io addon | `nextcloud_plugin.addon` | Django app (proxy file-node models, `UserSettings`/`NodeSettings`) |
| GravyValet foreign addon imp | `nextcloud_plugin.addon_imp` | WebDAV `StorageAddonHttpRequestorImp` |
| WaterButler provider | `nextcloud_plugin.provider` | WebDAV provider (`NextcloudProvider`) |

Ported from GakuNin RDM (`RDM-osf.io/addons/nextcloud`, `RDM-waterbutler/.../providers/nextcloud`).
Nextcloud speaks WebDAV, so the WaterButler provider and the GravyValet imp are closely
related to upstream's existing **ownCloud** support.

## Names to register (the values you must reference when configuring the hosts)

- WaterButler provider entry point / `wb_key`: **`nextcloud`**
- GravyValet `addon_imp_name`: **`NEXTCLOUD`** (or the package name `nextcloud_plugin.addon_imp`)
- osf.io addon Django app: **`nextcloud_plugin.addon`** (app label `addons_nextcloud`,
  `short_name` `nextcloud`)

## Install / use

### osf.io
1. `pip install nextcloud_plugin`
2. In `api/base/settings/local.py`: add `'nextcloud_plugin.addon'` to `INSTALLED_APPS`
   and `'nextcloud'` to `ADDONS_FOLDER_CONFIGURABLE`.
3. Add `'addons_nextcloud'` to `addons` in `addons.json` (and to `addons_default` /
   `addons_archivable` / `addons_commentable` if desired).
4. Apply the migration (see "Migration" below), then restart osf.io.

### GravyValet
1. `poetry add nextcloud_plugin` (or `pip install`).
2. In `app/settings`: add `'nextcloud_plugin.addon_imp'` to `INSTALLED_APPS` and a
   `"NEXTCLOUD": <id>` entry (id ≥ 5000) to `ADDON_IMPS`.
3. Restart GravyValet; then create `ExternalStorageService` rows with `wb_key="nextcloud"`.

### WaterButler
1. `poetry add nextcloud_plugin` (or `pip install`).
2. Restart WaterButler (the provider is discovered via the `waterbutler.providers`
   entry point).

## Status

This is a **scaffold**. See `SCOPING.md` for the porting delta analysis and the
list of remaining follow-up work (migration generation, the RDM-only `admin.rdm_addons`
import in `addon/views.py`, an addon_imp icon asset, and end-to-end validation against a
live Nextcloud instance).
