"""
OneShot - 选中文本获取服务
使用 Rust DLL (PyO3 扩展模块) 获取选中文本
"""

import logging
import os
import sys
import shutil
import tempfile
import importlib.util

logger = logging.getLogger(__name__)


class SelectionService:
    """获取鼠标选中文本的服务"""
    
    def __init__(self):
        """初始化选择服务"""
        self._pyd_path = None
        self._module = None
        self._init_pyd_path()
        self._load_pyd_once()
    
    def _init_pyd_path(self):
        """初始化 Rust PyO3 扩展模块路径"""
        # lib/ 与 services/ 同级，都在 oneshot/ 下
        # 使用 .pyd 扩展名，因为这是 Windows 上 Python 扩展模块的标准名称
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._pyd_path = os.path.join(base_dir, 'lib', 'selection.pyd')
        # 如果 .pyd 不存在，尝试 .dll
        if not os.path.exists(self._pyd_path):
            dll_path = os.path.join(base_dir, 'lib', 'selection.dll')
            if os.path.exists(dll_path):
                self._pyd_path = dll_path
    
    def _load_pyd_once(self):
        """只加载一次 PyO3 扩展模块"""
        if self._module is not None:
            return  # 已加载，跳过
        
        if not os.path.exists(self._pyd_path):
            logger.debug(f"Rust PyO3 扩展模块不存在: {self._pyd_path}")
            return
        
        try:
            # 复制到临时目录（Windows 要求）
            temp_dir = tempfile.mkdtemp(prefix="oneshot_selection_")
            temp_pyd = os.path.join(temp_dir, os.path.basename(self._pyd_path))
            shutil.copy(self._pyd_path, temp_pyd)
            
            # 加载 PyO3 扩展模块
            spec = importlib.util.spec_from_file_location('selection', temp_pyd)
            if spec is None or spec.loader is None:
                logger.debug("无法创建模块规范")
                return
            
            self._module = importlib.util.module_from_spec(spec)
            sys.modules['selection'] = self._module
            spec.loader.exec_module(self._module)
            
            logger.debug("Rust PyO3 扩展模块加载成功")
        except Exception as e:
            logger.debug(f"Rust PyO3 扩展模块加载失败: {e}")
            self._module = None
    
    def get_text(self) -> str:
        """
        获取当前选中的文本
        
        使用 Rust DLL (PyO3 扩展模块) 获取选中文本
        (Rust DLL 会先尝试 UI Automation，失败后 fallback 到模拟 Ctrl+C)
        
        Returns:
            选中的文本，如果失败则返回空字符串
        """
        if self._module is None:
            self._load_pyd_once()
            if self._module is None:
                logger.debug("Rust PyO3 扩展模块未加载")
                return ""
        
        try:
            # 调用 PyO3 模块中的 get_selected_text 函数
            result = self._module.get_selected_text()
            if result:
                text = str(result)
                if text:
                    logger.info(f"通过 Rust DLL 获取选中文本成功: [{text[:50]}...]" if len(text) > 50 else f"通过 Rust DLL 获取选中文本成功: [{text}]")
                    return text
            else:
                logger.debug("Rust DLL 返回空")
        except Exception as e:
            logger.warning(f"Rust DLL 调用失败: {e}")
            self._module = None  # 重置，下次重新加载
        
        return ""