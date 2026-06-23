"""GravyValet storage addon imp for Nextcloud.

Nextcloud speaks WebDAV. This imp targets the **user-relative** WebDAV endpoint
``/remote.php/webdav/`` (which resolves to the authenticated user's storage root
without needing the username in the URL) — the same endpoint the ported
WaterButler provider uses (``_webdav_url_``).

Design / contract:
  * ``api_base_url`` (the account's "Host URL") is the Nextcloud **base URL** — the
    host root, e.g. ``https://nextcloud.example/`` (GRDM parity). It is NOT a deep
    WebDAV path. The imp appends ``remote.php/webdav/`` to it for all requests.
  * The username is intentionally NOT required: for the username/password flow GV
    calls ``execute_post_auth_hook()`` with no extras, so ``auth_result_extras`` is
    empty and the credentials are not exposed to the imp. ``/remote.php/webdav/`` is
    relative to the authenticated user, so we don't need it.
  * ``build_wb_config`` emits ``{folder, host, verify_ssl}``; ``host`` is the base URL
    and the WaterButler provider appends ``/remote.php/webdav/`` itself.

Originally adapted from GravyValet's built-in ``addon_imps.storage.owncloud`` imp,
but reworked: that imp PROPFINDs ``api_base_url`` verbatim (so it requires a deep
WebDAV ``api_base_url``) and does a fragile current-user-principal two-step whose
URL joining only resolves from a host-root base. This version is host-root-first.

NOTE (follow-up): the ported WaterButler provider additionally supports file
*revisions* (Nextcloud version API) and, for the institutions flavor, the OCS
checksum API. Those richer capabilities are not surfaced through this imp's
browse/build_wb_config path and can be layered on if needed.
"""
import xml.etree.ElementTree as ET
from urllib.parse import (
    unquote,
    urlparse,
)

from rest_framework.exceptions import ValidationError

from addon_toolkit.interfaces import storage
from addon_toolkit.interfaces.storage import ItemType


# Nextcloud's legacy WebDAV endpoint, relative to api_base_url. It is scoped to the
# authenticated user, so (unlike /remote.php/dav/files/<username>/) it needs no username.
_WEBDAV_ROOT = "remote.php/webdav/"

_BUILD_PROPFIND_CURRENT_USER_PRINCIPAL = """<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:">
    <d:prop>
        <d:current-user-principal/>
    </d:prop>
</d:propfind>"""

_BUILD_PROPFIND_ALLPROPS = """<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:">
    <d:allprop/>
</d:propfind>"""


class NextcloudStorageImp(storage.StorageAddonHttpRequestorImp):
    async def get_external_account_id(self, auth_result_extras: dict[str, str]) -> str:
        # Validate the credentials by PROPFIND-ing the user's WebDAV root. The path
        # is relative, so it resolves against the host-root api_base_url correctly.
        try:
            async with self.network.PROPFIND(
                uri_path=self._dav_uri("/"),
                headers={"Depth": "0"},
                content=_BUILD_PROPFIND_CURRENT_USER_PRINCIPAL,
            ) as response:
                if response.http_status in (401, 403):
                    raise ValidationError("Invalid Nextcloud credentials (unauthorized).")
                if int(response.http_status) >= 400:
                    raise ValidationError(
                        "Please check the Host URL — it does not point to a valid "
                        "Nextcloud deployment."
                    )
                response_xml = await response.text_content()
        except ValueError as exc:
            # GravyvaletHttpRequestor raises ValueError for malformed/escaping URLs.
            if "base url" in str(exc).lower() or "scheme or host" in str(exc).lower():
                raise ValidationError(
                    "Invalid Host URL. Please check your Nextcloud base URL."
                )
            raise

        # Best-effort stable account id: the username in the current-user-principal
        # href (".../principals/users/<username>/"). A non-WebDAV response (HTML) means
        # the base URL is wrong; a WebDAV response that simply lacks the principal is
        # fine (we just return an empty id, as the s3compat imp does).
        try:
            principal = self._parse_current_user_principal(response_xml)
        except ET.ParseError:
            raise ValidationError(
                "Please check the Host URL — it does not point to a valid "
                "Nextcloud deployment."
            )
        except ValueError:
            return ""
        return principal.rstrip("/").rsplit("/", 1)[-1]

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        root_item = storage.ItemResult(
            item_id=_nextcloud_root_id(),
            item_name="Root Directory",
            item_type=ItemType.FOLDER,
            can_be_root=True,
            may_contain_root_candidates=True,
        )
        return storage.ItemSampleResult(items=[root_item])

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        _item_type, path = _parse_item_id(item_id)

        async with self.network.PROPFIND(
            uri_path=self._dav_uri(path),
            headers={"Depth": "0"},
            content=_BUILD_PROPFIND_ALLPROPS,
        ) as response:
            response_xml = await response.text_content()
            root = ET.fromstring(response_xml)
            response_element = root.find(
                "d:response", {"d": "DAV:", "oc": "http://owncloud.org/ns"}
            )
            if response_element is None:
                raise ValueError("No response element found in PROPFIND response")
            return self._parse_response_element(response_element, path)

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        _item_type, path = _parse_item_id(item_id)

        async with self.network.PROPFIND(
            uri_path=self._dav_uri(path),
            headers={"Depth": "1"},
            content=_BUILD_PROPFIND_ALLPROPS,
        ) as response:
            response_xml = await response.text_content()
            root = ET.fromstring(response_xml)
            items = []
            ns = {"d": "DAV:", "oc": "http://owncloud.org/ns"}
            for response_element in root.findall("d:response", ns):
                href_element = response_element.find("d:href", ns)
                if href_element is None or not href_element.text:
                    continue
                item_path = self._href_to_path(href_element.text)

                # skip the listed collection's own entry
                if item_path.rstrip("/") == path.rstrip("/"):
                    continue

                item_result = self._parse_response_element(response_element, item_path)
                if item_type is not None and item_result.item_type != item_type:
                    continue
                items.append(item_result)

            return storage.ItemSampleResult(items=items)

    def _dav_uri(self, path: str) -> str:
        """WebDAV request path (relative to api_base_url) for a logical storage path."""
        return _WEBDAV_ROOT + path.lstrip("/")

    async def build_wb_config(self) -> dict:
        # api_base_url is the Nextcloud base URL; the WaterButler provider appends
        # /remote.php/webdav/ to `host` itself, so pass the base URL through as-is.
        folder_path = ""
        if self.config.connected_root_id:
            _, subpath = _parse_item_id(self.config.connected_root_id)
            folder_path = subpath.strip("/")

        return {
            "folder": f"/{folder_path}",
            "host": self.config.external_api_url.rstrip("/"),
            "verify_ssl": True,
        }

    def _parse_response_element(
        self, response_element: ET.Element, path: str
    ) -> storage.ItemResult:
        ns = {"d": "DAV:", "oc": "http://owncloud.org/ns"}
        resourcetype = response_element.find(".//d:resourcetype", ns)
        item_type = (
            storage.ItemType.FOLDER
            if resourcetype is not None
            and resourcetype.find("d:collection", ns) is not None
            else storage.ItemType.FILE
        )
        displayname_element = response_element.find(".//d:displayname", ns)
        displayname = (
            displayname_element.text
            if displayname_element is not None and displayname_element.text
            else path.rstrip("/").split("/")[-1]
        )
        return storage.ItemResult(
            item_id=_make_item_id(item_type, path),
            item_name=displayname,
            item_type=item_type,
        )

    def _parse_current_user_principal(self, response_xml: str) -> str:
        ns = {"d": "DAV:"}
        root = ET.fromstring(response_xml)  # raises ET.ParseError on non-XML (HTML)
        element = root.find(".//d:current-user-principal/d:href", ns)
        if element is not None and element.text:
            return element.text
        raise ValueError("current-user-principal not found in response")

    def _href_to_path(self, href: str) -> str:
        """Map a WebDAV href back to a logical storage path (strip the endpoint prefix)."""
        href_path = urlparse(unquote(href)).path.lstrip("/")
        if href_path.startswith(_WEBDAV_ROOT):
            href_path = href_path[len(_WEBDAV_ROOT):]  # fmt: skip
        href_path = href_path.strip("/")
        return f"/{href_path}" if href_path else "/"


def _make_item_id(item_type: storage.ItemType, path: str) -> str:
    return f"{item_type.value}:{path}"


def _parse_item_id(item_id: str) -> tuple[storage.ItemType, str]:
    if not item_id:
        return ItemType.FOLDER, "/"
    _type, _path = item_id.split(":", maxsplit=1)
    return storage.ItemType(_type), _path


def _nextcloud_root_id() -> str:
    return _make_item_id(storage.ItemType.FOLDER, "/")
