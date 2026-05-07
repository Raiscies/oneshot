"""
OneShot - 选中文本获取服务
使用 Rust DLL 获取选中文本
"""

import logging
import os
import sys
import shutil
import importlib.util
import tempfile

logger = logging.getLogger(__name__)


class SelectionService:
    """获取鼠标选中文本的服务"""
    
    def __init__(self):
        """初始化选择服务"""
        self._dll_path = None
        self._pyd_path = None
        self._module = None
        self._init_dll_path()
        self._load_dll_once()
    
    def _init_dll_path(self):
        """初始化 Rust DLL 路径"""
        # lib/ 与 services/ 同级，都在 oneshot/ 下
        self._dll_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'lib', 'selection.dll'
        )
    
    def _load_dll_once(self):
        """只加载一次 DLL"""
        if self._module is not None:
            return  # 已加载，跳过
        
        try:
            if not os.path.exists(self._dll_path):
                logger.debug(f"Rust DLL 不存在: {self._dll_path}")
                return
            
            # 复制到临时目录
            temp_dir = tempfile.mkdtemp(prefix="oneshot_")
            self._pyd_path = os.path.join(temp_dir, 'selection.pyd')
            shutil.copy(self._dll_path, self._pyd_path)
            
            # 加载模块
            spec = importlib.util.spec_from_file_location('selection', self._pyd_path)
            if spec is None or spec.loader is None:
                logger.debug("无法创建模块规范")
                return
            
            self._module = importlib.util.module_from_spec(spec)
            sys.modules['selection'] = self._module
            spec.loader.exec_module(self._module)
            
            logger.debug("Rust DLL 加载成功")
            
        except Exception as e:
            logger.debug(f"Rust DLL 加载失败: {e}")
            self._module = None
    
    def get_text(self) -> str:
        """
        获取当前选中的文本
        
        使用 Rust DLL 获取选中文本
        (Rust DLL 会先尝试 UI Automation，失败后 fallback 到模拟 Ctrl+C)
        
        Returns:
            选中的文本，如果失败则返回空字符串
        """
        if self._module is None:
            self._load_dll_once()
            if self._module is None:
                logger.debug("Rust DLL 未加载")
                return ""
        
        try:
            result = self._module.get_selected_text()
            if result:
                logger.info(f"通过 Rust DLL 获取选中文本成功: [{result[:50]}...]" if len(result) > 50 else f"通过 Rust DLL 获取选中文本成功: [{result}]")
                return result
            else:
                logger.debug("Rust DLL 返回空")
        except Exception as e:
            logger.warning(f"Rust DLL 调用失败: {e}")
            self._module = None  # 重置，下次重新加载
        
        return ""
