"""
OneShot - CloudflareBypass 代理客户端

封装通过 CloudflareBypass 服务器代理 HTTP 请求的逻辑。
handler 中需要绕过 Cloudflare 防护时，通过 get_proxy() 获取单例即可。
"""

import asyncio
import logging
import sys
import threading
from pathlib import Path
from typing import Optional, Callable

import httpx
import uvicorn

logger = logging.getLogger(__name__)

CF_BYPASS_HOST = "127.0.0.1"
CF_BYPASS_PORT = 8000

# 将 third_party/cloudflarebypass 加入 sys.path 以导入 cf_bypasser
_CF_BYPASS_ROOT = Path(__file__).parent.parent.parent / "third_party" / "cloudflarebypass"
if str(_CF_BYPASS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CF_BYPASS_ROOT))

# ── 单例 ──────────────────────────────────────────────────

_instance: Optional["CloudflareBypassProxy"] = None


def get_proxy() -> Optional["CloudflareBypassProxy"]:
    """获取 CloudflareBypassProxy 单例"""
    return _instance


def set_proxy(proxy: "CloudflareBypassProxy"):
    """设置 CloudflareBypassProxy 单例（由 DownloadService 在初始化时调用）"""
    global _instance
    _instance = proxy


# ═══════════════════════════════════════════════════════════════

class CloudflareBypassProxy:
    """CloudflareBypass 代理管理器

    管理本地 CloudflareBypass 服务器的生命周期，
    并封装通过该代理下载文件的接口。
    handler 通过 get_proxy() 获取实例，无需关心 localhost:8000、x-hostname 等细节。

    用法:
        proxy = CloudflareBypassProxy()
        set_proxy(proxy)
        await proxy.start()
        path = await proxy.download(client, "/doi/pdf/10.1145/xxx", "dl.acm.org", dir)
        await proxy.stop()
    """

    def __init__(self, host: str = CF_BYPASS_HOST, port: int = CF_BYPASS_PORT):
        self._host = host
        self._port = port
        self._base_url = f"http://localhost:{port}"
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    # ── 生命周期 ──────────────────────────────────────────

    async def start(self):
        """启动 CloudflareBypass 服务器并等待就绪"""
        self._start_server()
        await self._wait_ready()

    async def stop(self):
        """停止 CloudflareBypass 服务器"""
        self._stop_server()

    # ── 下载接口 ──────────────────────────────────────────

    async def download(
        self,
        client: httpx.AsyncClient,
        path: str,
        target_host: str,
        download_dir: Path,
        filename: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Optional[Path]:
        """通过 CF bypass 代理下载文件

        Args:
            client: httpx 异步客户端
            path: 目标路径（如 /doi/pdf/10.1145/xxx）
            target_host: 目标域名（如 dl.acm.org），自动拼接 https://
            download_dir: 下载目录
            filename: 保存文件名，为 None 时自动从 path 推断
            progress_callback: 进度回调 (0.0 ~ 1.0)

        Returns:
            下载后的文件路径，失败返回 None
        """
        proxy_url = f"{self._base_url}{path}"
        headers = {"x-hostname": target_host}
        logger.info(f"CF 代理下载: {proxy_url} → https://{target_host}{path}")

        if not filename:
            filename = path.rstrip("/").rsplit("/", 1)[-1] or "download"
        file_path = download_dir / filename

        try:
            async with client.stream("GET", proxy_url, headers=headers, follow_redirects=False) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                if progress_callback:
                    progress_callback(0.0)
                with open(file_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(min(downloaded / total, 1.0))
                # 检查是否真的下载了内容（防止收到 HTML 错误页）
                if downloaded == 0 and total == 0:
                    raise RuntimeError("服务器返回空响应，可能不是有效的 PDF")
            logger.info(f"CF 代理下载完成: {file_path} ({downloaded} bytes)")
            return file_path
        except Exception as e:
            logger.error(f"CF 代理下载失败 [{type(e).__name__}]: {e}")
            if file_path.exists():
                file_path.unlink()
            return None

    # ── 服务器管理 ────────────────────────────────────────

    def _start_server(self):
        if self._server and self._thread and self._thread.is_alive():
            logger.debug("CloudflareBypass 服务器已在运行")
            return
        try:
            from cf_bypasser.server.app import create_app
        except ImportError:
            logger.warning("无法导入 cf_bypasser，CloudflareBypass 不可用")
            return

        logger.info("启动 CloudflareBypass 服务器（uvicorn 线程）")
        app = create_app()
        config = uvicorn.Config(app, host=self._host, port=self._port, log_level="info")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()

    def _stop_server(self):
        if self._server:
            logger.info("停止 CloudflareBypass 服务器")
            self._server.should_exit = True
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
            self._server = None
            self._thread = None

    async def _wait_ready(self, retries: int = 20, delay: float = 0.5):
        if not self._thread or not self._thread.is_alive():
            return
        for _ in range(retries):
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"{self._base_url}/cache/stats", timeout=2.0)
                    logger.info("CloudflareBypass 服务器已就绪")
                    return
            except httpx.ConnectError:
                pass
            except Exception:
                pass
            await asyncio.sleep(delay)
        logger.warning("CloudflareBypass 服务器可能未完全就绪")
