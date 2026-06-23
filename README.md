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
3. Add `'nextcloud'` (the addon `short_name`) to `addons` in `addons.json` (and to
   `addons_default` / `addons_archivable` / `addons_commentable` if desired).
4. Apply the migration (see "Migration" below), then restart osf.io.

#### Configuration (osf.io `api/base/settings/local.py`)

Per-deployment settings are read from the host osf.io Django settings (the same
`api/base/settings/local.py` used above), via `getattr` with built-in fallbacks — do
**not** edit files inside the installed package. All are optional:

| Setting | Type | Default | Meaning |
|---------|------|---------|---------|
| `NEXTCLOUD_USE_SSL` | bool | `True` | Verify the Nextcloud server's TLS certificate. |
| `NEXTCLOUD_MAX_UPLOAD_SIZE` | int (MB) | `5120` (5 × 1024) | Max file size the osf.io addon / front-end permits. |
| `NEXTCLOUD_DEFAULT_HOSTS` | list[str] | `[]` | Suggested Nextcloud hosts. Largely **vestigial**: in the GRDM2 (angular-osf + GravyValet) architecture the endpoint/host of a storage service lives on a GravyValet `ExternalStorageService`, not here. |

```python
# osf.io/api/base/settings/local.py
NEXTCLOUD_USE_SSL = True
NEXTCLOUD_MAX_UPLOAD_SIZE = 10 * 1024  # 10 GB
```

Per-service settings (endpoint host, per-service upload / concurrency limits, the
connected folder) are configured on the **GravyValet `ExternalStorageService`**, not in
these files.

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
