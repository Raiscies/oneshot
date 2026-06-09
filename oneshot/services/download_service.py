"""
OneShot - 文献下载服务

支持通过 URL 直接下载，以及通过 DOI 解析 → 出版商特定策略下载。
通过 CloudflareBypassProxy 管理本地 bypass 服务器生命周期。
"""

import asyncio
import logging
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

    def __init__(self, storage_dir: str = "", cf_host: str = "127.0.0.1", cf_port: int = 8000):
        self._storage_dir = Path(storage_dir) if storage_dir else Path.cwd() / "papers"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._publisher_handlers: dict[str, PublisherHandler] = {}
        self.cf_proxy = CloudflareBypassProxy(host=cf_host, port=cf_port)
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
    ) -> Optional[Path]:
        """通过 DOI 解析 → 出版商特定策略下载 PDF

        流程：
          1. 请求 https://doi.org/{doi} → 跟随重定向 → 获得出版商 URL
          2. 从 publisher URL 提取 hostname (如 dl.acm.org)
          3. 查找注册的 publisher handler → 调用下载
          4. 如无专用 handler → 直接返回 None（不支持该出版商）

        Args:
            doi: DOI 号（如 10.1145/123456）
            filename: 保存文件名
            progress_callback: 进度回调

        Returns:
            下载后的文件路径，失败返回 None
        """
        logger.info(f"DOI 下载: {doi}")

        # 每次下载用新的 AsyncClient，避免跨线程/事件循环共享问题
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            # Step 1: 解析 DOI → 出版商真实 URL
            publisher_url = await self._resolve_doi(client, doi)
            if not publisher_url:
                logger.error(f"无法解析 DOI: {doi}")
                return None

            hostname = urlparse(publisher_url).hostname or ""
            logger.info(f"出版商: {hostname} → {publisher_url[:80]}")

        # Step 2: 查找出版商处理器
            handler = self._publisher_handlers.get(hostname)
            if handler:
                logger.info(f"使用专用处理器: {hostname}")
                return await handler(client, doi, publisher_url, self._storage_dir,
                                     filename, progress_callback)

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
