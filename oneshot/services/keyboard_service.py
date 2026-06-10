"""
OneShot - 全局快捷键监听服务
使用 multiprocessing + keyboard 库实现全局快捷键监听
"""

import logging
import multiprocessing
import time
import threading
from typing import Callable, Optional

import keyboard

logger = logging.getLogger(__name__)


def _keyboard_worker(pipe, stop_event, hotkey_str):
    """
    独立的键盘监听进程
    
    Args:
        pipe: 与主进程通信的管道
        stop_event: 停止信号事件
        hotkey_str: 热键字符串，如 "ctrl+q"
    """
    logger.info(f"键盘监听进程启动，热键: {hotkey_str}")
    
    handler = None
    
    def on_hotkey():
        """热键按下时的回调"""
        logger.info("热键触发")
        # 通过管道通知主进程
        try:
            pipe.send("trigger")
        except Exception:
            pass
    
    try:
        # 注册热键
        handler = keyboard.add_hotkey(hotkey_str, on_hotkey, suppress=False)
        logger.info(f"热键已注册: {hotkey_str}")
        
        # 阻塞等待直到收到停止信号或中断
        try:
            stop_event.wait()
        except KeyboardInterrupt:
            pass  # 安静退出
    finally:
        # 清理热键
        if handler:
            try:
                keyboard.remove_hotkey(handler)
            except Exception:
                pass
        logger.info("键盘监听进程已停止")


class KeyboardService:
    """全局键盘监听服务"""
    
    def __init__(self):
        """初始化键盘服务"""
        self._process: Optional[multiprocessing.Process] = None
        self._pipe = None
        self._stop_event = None
        self._callback: Optional[Callable] = None
        self._modifier_keys = set()
        self._hotkey = ({"ctrl"}, "q")  # 默认 Ctrl+Q
        self._hotkey_str = "ctrl+q"
    
    @property
    def is_alive(self) -> bool:
        """检查键盘监听子进程是否存活"""
        return self._process is not None and self._process.is_alive()
    
    def set_hotkey(self, callback: Callable, modifier: set = None, key: str = None):
        """
        设置快捷键
        
        Args:
            callback: 按键触发回调
            modifier: 修饰键集合，如 {'ctrl', 'shift', 'alt'}
            key: 主键，如 'l', 's' 等
        """
        self._callback = callback
        
        if modifier is not None:
            self._modifier_keys = modifier
        if key is not None:
            self._hotkey = (self._modifier_keys, key.lower())
        
        # 构建热键字符串
        modifiers = sorted(self._hotkey[0])
        key_char = self._hotkey[1]
        self._hotkey_str = "+".join(modifiers + [key_char])
        
        # 停止旧进程
        self.stop()
        
        # 启动新进程
        self._start_worker()
        
        logger.info(f"快捷键已设置: {self._hotkey_str.upper()}")
    
    def _start_worker(self):
        """启动键盘监听进程"""
        # 创建管道用于进程间通信
        self._pipe, child_pipe = multiprocessing.Pipe()
        
        # 创建停止事件
        self._stop_event = multiprocessing.Event()
        
        # 启动独立进程
        self._process = multiprocessing.Process(
            target=_keyboard_worker,
            args=(child_pipe, self._stop_event, self._hotkey_str)
        )
        self._process.daemon = True
        self._process.start()
        
        # 启动管道监听线程
        threading.Thread(target=self._listen_pipe, daemon=True).start()
    
    def _listen_pipe(self):
        """监听管道，接收子进程消息"""
        try:
            while self._process and self._process.is_alive():
                try:
                    if self._pipe and self._pipe.poll(0.1):
                        msg = self._pipe.recv()
                        if msg == "trigger" and self._callback:
                            self._callback()
                except (EOFError, BrokenPipeError, ConnectionResetError):
                    break
                except Exception:
                    break
        finally:
            logger.debug("管道监听线程退出")
    
    def stop(self):
        """停止键盘监听"""
        if self._stop_event:
            self._stop_event.set()
        
        if self._process:
            try:
                self._process.join(timeout=1)
                if self._process.is_alive():
                    self._process.terminate()
            except Exception:
                pass
            self._process = None
        
        if self._pipe:
            try:
                self._pipe.close()
            except Exception:
                pass
            self._pipe = None
        
        self._stop_event = None
        logger.debug("KeyboardService 已停止")
    
    def remove_hotkey(self):
        """移除快捷键（调用 stop）"""
        self.stop()