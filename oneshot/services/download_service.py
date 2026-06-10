"""
OneShot - 文献下载服务

支持通过 URL 直接下载，以及通过 DOI 解析 → 出版商特定策略下载。
通过 CloudflareBypassProxy 管理本地 bypass 服务器生命周期。
"""

import asyncio
import json
import logging
import re
import time
import threading
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse

import httpx

from .handlers.cf_proxy import CloudflareBypassProxy, set_proxy as _set_cf_proxy
from .handlers.default_handler import stream_download_file
from .handlers import register_all as _register_all_handlers

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 出版商处理器类型
# ═══════════════════════════════════════════════════════════════
PublisherHandler = Callable[..., object]
"""
出版商处理器签名:
    async def handler(
        client: httpx.AsyncClient,
        doi: str,
        publisher_url: str,      # doi.org 跳转后的真实 URL
        download_dir: Path,      # 下载目标目录
        filename: Optional[str] = None,
        progress_cb: Optional[Callable] = None
    ) -> Optional[Path]          # 返回下载文件路径，失败返回 None
"""


# ═══════════════════════════════════════════════════════════════
# 下载清单 & 命名规则
# ═══════════════════════════════════════════════════════════════

_DEFAULT_NAMING = "{doi}.pdf"

class DownloadManifest:
    """DOI → 文件名映射。支持用户重命名后仍能定位已下载文件。"""

    def __init__(self, storage_dir: Path):
        self._path = storage_dir / "manifest.json"
        self._records: dict[str, str] = {}  # doi → filename

    def load(self):
        if self._path.exists():
            try:
                self._records = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._records = {}

    def save(self):
        self._path.write_text(json.dumps(self._records, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, doi: str, storage_dir: Path) -> Optional[Path]:
        fname = self._records.get(doi)
        if not fname:
            return None
        path = storage_dir / fname
        return path if path.exists() and path.stat().st_size > 0 else None

    def set(self, doi: str, filename: str):
        self._records[doi] = filename
        self.save()


# ═══════════════════════════════════════════════════════════════
# 文件名生成（基于 dict 映射，易于扩展占位符）
# ═══════════════════════════════════════════════════════════════

def _sanitize(text: str) -> str:
    """清理文件名中的非法字符"""
    return re.sub(r'[<>:"/\\|?*$]', '', text)

def _build_placeholder_map(doi: str, meta: dict) -> dict[str, str]:
    """构建占位符 → 值映射。新增占位符只需在此加一行。"""
    from datetime import date

    safe_doi = doi.replace("/", "_")
    title = meta.get("title", "")
    title = re.sub(r'\s+', ' ', _sanitize(title))[:80].strip()
    authors = meta.get("authors", [])
    first_author = _sanitize(authors[0]) if authors else ""
    pubdate = str(meta.get("pubdate", ""))

    return {
        "{doi}":       safe_doi,
        "{title}":     title,
        "{author}":    first_author,
        "{pubdate}":   pubdate,
        "{downdate}":  date.today().isoformat(),
    }

def build_filename(pattern: str, doi: str, meta: Optional[dict] = None) -> str:
    """用命名格式和元数据生成文件名。"""
    meta = meta or {}
    replacements = _build_placeholder_map(doi, meta)

    result = pattern
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    result = result.strip('. ')
    if not result or result == pattern:
        result = f"{doi.replace('/', '_')}.pdf"
    return result


# ═══════════════════════════════════════════════════════════════
# 下载服务
# ═══════════════════════════════════════════════════════════════

class DownloadService:
    """文献下载服务

    功能:
    - 通过 URL 直接下载文件
    - 通过 DOI 解析出版商并调用对应处理器下载 PDF
    - 自动管理 CloudflareBypass 代理服务器
    - 可扩展的出版商处理器注册机制
    """

    def __init__(self, storage_dir: str = "", cf_host: str = "127.0.0.1", cf_port: int = 8000, cf_external: bool = False,
                 naming_pattern: str = _DEFAULT_NAMING, delay_seconds: int = 5):
        self._storage_dir = Path(storage_dir) if storage_dir else Path.cwd() / "papers"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._manifest = DownloadManifest(self._storage_dir)
        self._manifest.load()
        self._naming_pattern = naming_pattern
        self._delay_seconds = delay_seconds
        self._publisher_last_time: dict[str, float] = {}
        self._publisher_lock = threading.Lock()
        self._publisher_handlers: dict[str, PublisherHandler] = {}
        self.cf_proxy = CloudflareBypassProxy(host=cf_host, port=cf_port, external=cf_external)
        _set_cf_proxy(self.cf_proxy)
        _register_all_handlers(self)

    # ── 生命周期 ──────────────────────────────────────────────

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()

    async def start(self):
        """启动服务：拉起 CloudflareBypass 代理"""
        await self.cf_proxy.start()

    async def stop(self):
        """停止服务"""
        await self.cf_proxy.stop()

    # ── 公开接口 ──────────────────────────────────────────────

    async def download_by_url(
        self,
        url: str,
        filename: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Optional[Path]:
        """直接通过 URL 下载文件（不经过 DOI 解析）"""
        if not filename:
            filename = self._filename_from_url(url)
        file_path = self._storage_dir / filename
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            return await self._stream_download(client, url, file_path, progress_callback)

    async def download_by_doi(
        self,
        doi: str,
        filename: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
        meta: Optional[dict] = None,
    ) -> Optional[Path]:
        """通过 DOI 解析 → 出版商特定策略下载 PDF

        流程：
          1. 请求 https://doi.org/{doi} → 跟随重定向 → 获得出版商 URL
          2. 从 publisher URL 提取 hostname (如 dl.acm.org)
          3. 查找注册的 publisher handler → 调用下载
          4. 如无专用 handler → 直接返回 None（不支持该出版商）

        Args:
            doi: DOI 号
            filename: 保存文件名（为 None 则用命名规则生成）
            progress_callback: 进度回调
            meta: 文献元数据 {"title": ..., "authors": [...], "pubdate": ...}
        """
        logger.info(f"DOI 下载: {doi}")

        # 如果已存在则跳过（从 manifest 查找，不依赖文件名）
        existing = self.check_file_exists(doi)
        if existing:
            logger.info(f"文件已存在，跳过下载: {existing}")
            return existing

        # 统一计算文件名
        if not filename:
            filename = build_filename(self._naming_pattern, doi, meta)

        # 每次下载用新的 AsyncClient，避免跨线程/事件循环共享问题
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            # Step 1: 解析 DOI → 出版商真实 URL
            publisher_url = await self._resolve_doi(client, doi)
            if not publisher_url:
                logger.error(f"无法解析 DOI: {doi}")
                return None

            hostname = urlparse(publisher_url).hostname or ""
            logger.info(f"出版商: {hostname} → {publisher_url[:80]}")

            # 按出版商限流
            self._rate_limit(hostname)

        # Step 2: 查找出版商处理器
            handler = self._publisher_handlers.get(hostname)
            if handler:
                logger.info(f"使用专用处理器: {hostname}")
                path = await handler(client, doi, publisher_url, self._storage_dir,
                                     filename, progress_callback)
                if path:
                    self._manifest.set(doi, path.name)
                return path

            # 无专用处理器 → 暂不支持下载
            logger.info(f"出版商 {hostname} 未注册处理器，暂不支持下载")
            return None

    def register_handler(self, hostname: str, handler: PublisherHandler):
        """注册出版商处理器

        Args:
            hostname: 出版商域名（如 dl.acm.org）
            handler: async def handler(client, doi, pub_url, dir, filename, progress_cb) -> Path | None
        """
        self._publisher_handlers[hostname] = handler
        logger.info(f"已注册出版商处理器: {hostname}")

    def get_pdf_path(self, doi: str) -> Path:
        """根据 DOI + 命名规则返回默认文件名路径"""
        filename = build_filename(self._naming_pattern, doi)
        return self._storage_dir / filename

    def check_file_exists(self, doi: str) -> Optional[Path]:
        """从 manifest 查找已下载文件，不依赖文件名"""
        return self._manifest.get(doi, self._storage_dir)

    def _rate_limit(self, hostname: str):
        """按出版商限流，确保同一出版商请求间隔至少 _delay_seconds 秒"""
        if self._delay_seconds <= 0:
            return
        with self._publisher_lock:
            last = self._publisher_last_time.get(hostname, 0)
            elapsed = time.time() - last
            if elapsed < self._delay_seconds:
                wait = self._delay_seconds - elapsed
                logger.debug(f"限流 {hostname}: 等待 {wait:.1f}s")
            self._publisher_last_time[hostname] = time.time() + max(0, self._delay_seconds - elapsed)
        if elapsed < self._delay_seconds:
            time.sleep(self._delay_seconds - elapsed)

    # ── DOI 解析 ──────────────────────────────────────────────

    @staticmethod
    async def _resolve_doi(client: httpx.AsyncClient, doi: str) -> Optional[str]:
        """解析 DOI → 获取出版商真实 URL

        请求 https://doi.org/{doi}，跟随重定向链，只关心最终跳转到的 hostname。
        即使最终目标返回 403（如 Cloudflare 拦截），只要拿到了 hostname 就算成功。
        """
        doi_url = f"https://doi.org/{doi}"
        try:
            resp = await client.get(doi_url, follow_redirects=True)
            # 不 raise_for_status：403 也算成功，因为我们只需要 resp.url
            final_url = str(resp.url)
            logger.debug(f"DOI {doi} → {final_url} (status={resp.status_code})")
            return final_url
        except Exception as e:
            logger.error(f"DOI 解析失败: {e}")
            return None

    # ── 通用流式下载 ──────────────────────────────────────────

    @staticmethod
    async def _stream_download(
        client: httpx.AsyncClient,
        url: str,
        file_path: Path,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Optional[Path]:
        return await stream_download_file(client, url, file_path, progress_callback)

    # ── 文件名生成 ────────────────────────────────────────────

    @staticmethod
    def _filename_from_url(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        name = path.rsplit("/", 1)[-1] if path else "download"
        return name if name else "download"
