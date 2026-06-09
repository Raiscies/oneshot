"""
OneShot - 配置服务
管理程序配置，包括快捷键设置等
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    "hotkey": {
        "modifiers": ["ctrl"],
        "key": "q"
    },
    "window": {
        "always_on_top": True,
        "follow_mouse": True
    },
    "storage": {
        "path": ""  # 空字符串表示使用默认路径
    },
    "cf_bypass": {
        "host": "127.0.0.1",
        "port": 8000
    },
    "download": {
        "auto_open_pdf": False,
        "auto_download_count": 1
    },
    "search": {
        "engine_url": "https://scholar.google.com/scholar?q={query}"
    }
}


class ConfigService:
    """配置服务"""
    
    def __init__(self, config_path: Path = None):
        """
        初始化配置服务
        
        Args:
            config_path: 配置文件路径，默认使用项目根目录下的 config.json
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.json"
        
        self.config_path = config_path
        self._config = DEFAULT_CONFIG.copy()
        self._load()
    
    def _load(self):
        """加载配置文件"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 合并配置，保留默认值
                    self._merge_config(loaded)
                logger.info(f"配置已加载: {self.config_path}")
            except Exception as e:
                logger.warning(f"加载配置失败，使用默认值: {e}")
        else:
            logger.info("配置文件不存在，使用默认值，将自动创建")
            # 自动创建默认配置文件
            self.save()
    
    def _merge_config(self, loaded: Dict[str, Any]):
        """合并加载的配置"""
        for section, values in loaded.items():
            if section in self._config and isinstance(values, dict):
                self._config[section].update(values)
            else:
                self._config[section] = values
    
    def save(self):
        """保存配置到文件"""
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            
            logger.info(f"配置已保存: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def get(self, section: str, key: str = None, default=None):
        """
        获取配置值
        
        Args:
            section: 配置section
            key: 配置键，如果为None则返回整个section
            default: 默认值
        """
        if section not in self._config:
            return default
        
        if key is None:
            return self._config[section]
        
        return self._config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Any):
        """
        设置配置值
        
        Args:
            section: 配置section
            key: 配置键
            value: 配置值
        """
        if section not in self._config:
            self._config[section] = {}
        
        self._config[section][key] = value
    
    @property
    def hotkey(self) -> Dict[str, Any]:
        """获取快捷键配置"""
        return self._config.get("hotkey", DEFAULT_CONFIG["hotkey"])
    
    @property
    def window(self) -> Dict[str, Any]:
        """获取窗口配置"""
        return self._config.get("window", DEFAULT_CONFIG["window"])
    
    @property
    def storage(self) -> Dict[str, Any]:
        """获取存储配置"""
        return self._config.get("storage", DEFAULT_CONFIG["storage"])

    @property
    def cf_bypass(self) -> Dict[str, Any]:
        """获取 CloudflareBypass 配置"""
        return self._config.get("cf_bypass", DEFAULT_CONFIG["cf_bypass"])

    @property
    def download(self) -> Dict[str, Any]:
        """获取下载配置"""
        return self._config.get("download", DEFAULT_CONFIG["download"])

    @property
    def search(self) -> Dict[str, Any]:
        """获取搜索配置"""
        return self._config.get("search", DEFAULT_CONFIG["search"])