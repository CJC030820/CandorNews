"""Local copies of publisher article images.

Some publishers (for example Bernama) intermittently refuse connections from
browsers or block image hot-linking, so their images fail to load in the feed.
The worker downloads each new article's image once at collection time, while
the publisher is reachable, and the API serves that copy as a fallback.

Only public http(s) hosts are fetched: hosts that resolve to private,
loopback, link-local or reserved addresses are refused, including on
redirects, so a feed cannot make the server fetch internal resources.
"""
from concurrent.futures import ThreadPoolExecutor
import glob
import hashlib
import ipaddress
import logging
import os
import socket
from pathlib import Path
from typing import Iterable, Optional, Tuple
from urllib.parse import urljoin, urlparse

import certifi
import requests

logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.getenv("IMAGE_CACHE_DIR", Path(__file__).resolve().parents[2] / "image_cache"))
MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = 8
MAX_REDIRECTS = 3
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CandorNewsBot/1.0)", "Accept": "image/*"}
# Retry newly collected articles' images that are still missing (per cycle).
BACKFILL_LIMIT = 60


def _ca_bundle() -> str:
    """Standard trusted roots plus intermediate certificates some publishers
    forget to send (see app/certs). Verification stays fully enabled."""
    extra = sorted(glob.glob(str(Path(__file__).resolve().parents[1] / "certs" / "*.pem")))
    if not extra:
        return certifi.where()
    bundle = Path(os.getenv("IMAGE_CA_BUNDLE", Path(__file__).resolve().parents[2] / ".image-ca-bundle.pem"))
    try:
        parts = [Path(certifi.where()).read_text(encoding="utf-8")] + [Path(p).read_text(encoding="utf-8") for p in extra]
        bundle.write_text("\n".join(parts), encoding="utf-8")
        return str(bundle)
    except OSError:
        return certifi.where()


CA_BUNDLE = _ca_bundle()


def source_candidates(url: str) -> list:
    """Addresses to try for an image. Bernama publishes og:image links on
    www.bernama.com that return 404; the same photo is served by
    web14.bernama.com (with or without the "-medium" size suffix)."""
    candidates = []
    try:
        parsed = urlparse(url)
    except ValueError:
        return [url]
    host = (parsed.hostname or "").lower()
    if host.endswith("bernama.com") and parsed.path.startswith("/storage/photos/"):
        for path in dict.fromkeys([parsed.path, parsed.path.replace("-medium", "")]):
            candidates.append(f"https://web14.bernama.com{path}")
    candidates.append(url)
    return list(dict.fromkeys(candidates))


def _key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def is_public_http_url(url: Optional[str]) -> bool:
    try:
        parsed = urlparse(url or "")
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except (ValueError, OSError):
        return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0].split("%")[0])
        if not address.is_global:
            return False
    return bool(infos)


def cached(url: Optional[str]) -> Optional[Tuple[Path, str]]:
    """Return (file path, content type) when an image for this URL is stored."""
    if not url:
        return None
    path = CACHE_DIR / _key(url)
    type_path = path.with_suffix(".type")
    if path.is_file() and type_path.is_file():
        return path, type_path.read_text(encoding="utf-8").strip() or "image/jpeg"
    return None


def download(url: Optional[str]) -> bool:
    """Download one image into the cache (stored under the article's image
    URL). Tries the publisher's working image address first, then the
    original. Returns True when a copy is stored."""
    if not url or cached(url):
        return bool(url)
    for candidate in source_candidates(url):
        for _attempt in range(2):  # one retry for a slow/timed-out server
            result = _fetch(candidate, url)
            if result is not None:
                if result:
                    return True
                break
    return False


def _fetch(source: str, key_url: str) -> Optional[bool]:
    """True = stored; False = this address does not serve an image;
    None = network error worth one retry."""
    current = source
    try:
        for _ in range(MAX_REDIRECTS + 1):
            if not is_public_http_url(current):
                return False
            with requests.get(current, headers=HEADERS, timeout=TIMEOUT, stream=True,
                              allow_redirects=False, verify=CA_BUNDLE) as response:
                if response.is_redirect or response.is_permanent_redirect:
                    current = urljoin(current, response.headers.get("Location", ""))
                    continue
                content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                if response.status_code != 200 or not content_type.startswith("image/"):
                    return False
                data = bytearray()
                for chunk in response.iter_content(64 * 1024):
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        return False
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                path = CACHE_DIR / _key(key_url)
                tmp = path.with_suffix(".part")
                tmp.write_bytes(bytes(data))
                path.with_suffix(".type").write_text(content_type, encoding="utf-8")
                os.replace(tmp, path)
                return True
        return False
    except requests.RequestException as exc:  # timeouts, resets: retry once
        logger.debug(f"Could not fetch image {source}: {exc}")
        return None
    except Exception as exc:  # anything else must never break collection
        logger.debug(f"Could not cache image {source}: {exc}")
        return False


def download_many(urls: Iterable[Optional[str]]) -> int:
    targets = list(dict.fromkeys(u for u in urls if u and not cached(u)))
    if not targets:
        return 0
    with ThreadPoolExecutor(max_workers=min(6, len(targets))) as executor:
        return sum(executor.map(download, targets))
