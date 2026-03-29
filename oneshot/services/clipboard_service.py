"""
OneShot - 剪贴板服务
"""

import logging
import pyperclip

logger = logging.getLogger(__name__)


class ClipboardService:
    """剪贴板服务"""
    
    def __init__(self):
        """初始化剪贴板服务"""
        self._last_content = ""
    
    def get_text(self) -> str:
        """
        获取剪贴板文本
        
        Returns:
            剪贴板内容
        """
        try:
            text = pyperclip.paste()
            # 清理空白字符
            text = text.strip()
            
            if text:
                logger.debug(f"读取剪贴板: {text[:50]}...")
            else:
                logger.debug("剪贴板为空")
            
            return text
            
        except Exception as e:
            logger.error(f"读取剪贴板失败: {e}")
            return ""
    
    def set_text(self, text: str) -> bool:
        """
        设置剪贴板文本
        
        Args:
            text: 要设置的文本
            
        Returns:
            是否成功
        """
        try:
            pyperclip.copy(text)
            self._last_content = text
            logger.debug(f"写入剪贴板: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"写入剪贴板失败: {e}")
            return False
    
    def has_new_content(self) -> bool:
        """
        检查剪贴板是否有新内容
        
        Returns:
            是否有新内容
        """
        current = self.get_text()
        if current and current != self._last_content:
            self._last_content = current
            return True
        return False
    
    def get_if_new(self) -> str:
        """
        如果有新内容则获取
        
        Returns:
            新内容或空字符串
        """
        if self.has_new_content():
            return self._last_content
        return ""
