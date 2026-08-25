from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


class OfficialDownloadError(RuntimeError):
    pass


OFFICIAL_HOSTS = {"openapi.twse.com.tw", "www.tpex.org.tw", "mops.twse.com.tw"}


def validate_official_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS:
        raise OfficialDownloadError(f"只允許 HTTPS 官方來源：{url}")


def fetch_bytes(url, timeout=30, retries=3, max_bytes=100_000_000, delay=1.0):
    validate_official_url(url)
    last_error = None
    for attempt in range(retries):
        try:
            request = Request(url, headers={"Accept":"application/json,application/xml,text/html,*/*",
                                            "User-Agent":"TW-Rank-Research/0.8"})
            with urlopen(request, timeout=timeout) as response:
                length = response.headers.get("Content-Length")
                if length and int(length) > max_bytes:
                    raise OfficialDownloadError(f"官方檔案超過大小限制：{length} bytes")
                payload = response.read(max_bytes + 1)
                if len(payload) > max_bytes:
                    raise OfficialDownloadError("官方檔案超過大小限制")
                return payload, dict(response.headers)
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt + 1 < retries:
                time.sleep(delay * (2 ** attempt))
    raise OfficialDownloadError(f"官方下載失敗：{url}｜{last_error}")


def download_to_file(url, destination, timeout=30, retries=3, max_bytes=100_000_000):
    """Download with a .part file and HTTP Range resume when the server supports it."""
    validate_official_url(url)
    destination = Path(destination); partial = destination.with_suffix(destination.suffix + ".part")
    last_error = None
    for attempt in range(retries):
        existing = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent":"TW-Rank-Research/0.8"}
        if existing:
            headers["Range"] = f"bytes={existing}-"
        try:
            with urlopen(Request(url, headers=headers), timeout=timeout) as response:
                status = getattr(response, "status", response.getcode())
                resume = existing > 0 and status == 206
                if existing and not resume:
                    existing = 0
                mode = "ab" if resume else "wb"
                response_headers = dict(response.headers)
                with partial.open(mode) as file:
                    total = existing
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        total += len(block)
                        if total > max_bytes:
                            raise OfficialDownloadError("官方檔案超過大小限制")
                        file.write(block)
            partial.replace(destination)
            return destination, response_headers
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise OfficialDownloadError(f"官方檔案下載失敗：{url}｜{last_error}")


class SwaggerOfficialAdapter:
    """Discover endpoints from an official Swagger document instead of hardcoding paths."""

    def __init__(self, swagger_url, output_directory, summary_keywords, max_endpoints=20):
        self.swagger_url = swagger_url
        self.output_directory = Path(output_directory)
        self.summary_keywords = tuple(summary_keywords)
        self.max_endpoints = max_endpoints

    def discover(self, spec):
        endpoints = []
        for path, operations in spec.get("paths", {}).items():
            operation = operations.get("get", {})
            summary = operation.get("summary", "")
            if any(keyword in summary for keyword in self.summary_keywords):
                endpoints.append((path, summary))
        return endpoints[:self.max_endpoints]

    def sync(self):
        payload, _ = fetch_bytes(self.swagger_url)
        spec = json.loads(payload.decode("utf-8-sig"))
        parsed = urlparse(self.swagger_url)
        base_path = spec.get("basePath", "")
        base_url = f"{parsed.scheme}://{parsed.netloc}{base_path.rstrip('/')}/"
        endpoints = self.discover(spec)
        if not endpoints:
            raise OfficialDownloadError("Swagger 中找不到符合關鍵字的資料端點")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.output_directory / stamp
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "swagger.json").write_bytes(payload)
        manifest = {"swagger_url":self.swagger_url,"fetched_at":stamp,"datasets":[]}
        for index, (path, summary) in enumerate(endpoints, start=1):
            url = urljoin(base_url, path.lstrip("/"))
            data, headers = fetch_bytes(url)
            filename = f"dataset_{index:02d}.json"
            (run_dir / filename).write_bytes(data)
            try:
                decoded = json.loads(data.decode("utf-8-sig"))
                rows = len(decoded) if isinstance(decoded, list) else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                rows = None
            manifest["datasets"].append({"path":path,"summary":summary,"url":url,"file":filename,
                "rows":rows,"sha256":hashlib.sha256(data).hexdigest(),
                "content_type":headers.get("Content-Type","")})
            time.sleep(0.25)
        (run_dir / "manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        return run_dir, manifest


class _DownloadLinkParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href", "")
        if href.lower().split("?", 1)[0].endswith((".zip", ".xbrl", ".xml")):
            self.links.append(href)


class MopsPublicFileAdapter:
    """Download only public file links exposed by an official MOPS index page."""

    def __init__(self, index_url, output_directory, filename_contains=None, max_files=50):
        self.index_url = index_url
        self.output_directory = Path(output_directory)
        self.filename_contains = tuple(filename_contains or ())
        self.max_files = max_files

    def sync(self):
        html, _ = fetch_bytes(self.index_url, max_bytes=20_000_000)
        parser = _DownloadLinkParser(); parser.feed(html.decode("utf-8-sig", errors="replace"))
        links = []
        for href in parser.links:
            url = urljoin(self.index_url, href)
            validate_official_url(url)
            if urlparse(url).hostname != urlparse(self.index_url).hostname:
                continue
            if self.filename_contains and not all(token in url for token in self.filename_contains):
                continue
            if url not in links:
                links.append(url)
        links = links[:self.max_files]
        if not links:
            raise OfficialDownloadError("官方頁面沒有符合條件的公開 XBRL／XML／ZIP 連結")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.output_directory / stamp; run_dir.mkdir(parents=True, exist_ok=False)
        manifest = {"index_url":self.index_url,"fetched_at":stamp,"files":[]}
        for index,url in enumerate(links,start=1):
            basename = Path(urlparse(url).path).name or f"official_{index:03d}.bin"
            filename = f"{index:03d}_{basename}"
            path,headers = download_to_file(url, run_dir / filename)
            data = path.read_bytes()
            manifest["files"].append({"url":url,"file":filename,"size":len(data),
                "sha256":hashlib.sha256(data).hexdigest(),"content_type":headers.get("Content-Type","")})
            time.sleep(0.5)
        (run_dir / "manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        return run_dir, manifest
