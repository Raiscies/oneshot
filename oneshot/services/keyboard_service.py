"""
OneShot - 全局快捷键监听服务
"""

import logging
from typing import Callable, Optional
from threading import Thread, Event
import asyncio

logger = logging.getLogger(__name__)


class KeyboardService:
    """全局键盘监听服务"""
    
    def __init__(self):
        """初始化键盘服务"""
        self._running = False
        self._thread: Optional[Thread] = None
        self._stop_event = Event()
        self._callback: Optional[Callable] = None
        self._modifier_keys = set()
        self._hotkey = ({"ctrl", "shift"}, "l")  # 默认 Ctrl+Shift+L
    
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
        
        logger.info(f"快捷键已设置: {'+'.join(sorted(self._hotkey[0]))}+{self._hotkey[1].upper()}")
    
    def start(self):
        """启动键盘监听"""
        if self._running:
            logger.warning("键盘监听已在运行")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info("键盘监听已启动")
    
    def stop(self):
        """停止键盘监听"""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=2)
        
        logger.info("键盘监听已停止")
    
    def _listen(self):
        """监听循环"""
        try:
            from pynput import keyboard
        except ImportError:
            logger.error("pynput未安装，请运行: pip install pynput")
            self._running = False
            return
        
        def on_press(key):
            """按键按下处理"""
            try:
                # 获取当前修饰键状态
                current_modifiers = set()
                
                if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    current_modifiers.add("ctrl")
                elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                    current_modifiers.add("shift")
                elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                    current_modifiers.add("alt")
                
                # 检查是否是主键
                try:
                    key_char = key.char.lower()
                except AttributeError:
                    key_char = None
                
                # 检查是否匹配快捷键
                expected_modifiers, expected_key = self._hotkey
                
                if key_char == expected_key:
                    if current_modifiers == expected_modifiers or \
                       (current_modifiers.issuperset(expected_modifiers) and 
                        not current_modifiers - expected_modifiers):
                        logger.info("检测到快捷键触发")
                        if self._callback:
                            # 在新线程中调用回调
                            Thread(target=self._trigger_callback, daemon=True).start()
                else:
                    # 检查修饰键是否按下
                    if "ctrl" in current_modifiers:
                        self._modifier_keys.add("ctrl")
                    if "shift" in current_modifiers:
                        self._modifier_keys.add("shift")
                    if "alt" in current_modifiers:
                        self._modifier_keys.add("alt")
                        
            except Exception as e:
                logger.error(f"按键处理错误: {e}")
        
        def on_release(key):
            """按键释放处理"""
            try:
                try:
                    key_char = key.char.lower()
                except AttributeError:
                    key_char = None
                
                # 释放修饰键
                if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    self._modifier_keys.discard("ctrl")
                elif key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
                    self._modifier_keys.discard("shift")
                elif key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
                    self._modifier_keys.discard("alt")
                    
            except Exception as e:
                logger.error(f"按键释放处理错误: {e}")
        
        # 改进的监听逻辑
        pressed_keys = set()
        
        def on_press_v2(key):
            try:
                key_name = None
                is_modifier = False
                
                # 处理修饰键
                if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                    pressed_keys.add("ctrl")
                    is_modifier = True
                elif key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                    pressed_keys.add("shift")
                    is_modifier = True
                elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                    pressed_keys.add("alt")
                    is_modifier = True
                
                # 处理普通键
                if not is_modifier:
                    try:
                        key_name = key.char.lower()
                    except AttributeError:
                        return
                    
                    pressed_keys.add(key_name)
                    
                    # 检查快捷键
                    expected_modifiers, expected_key = self._hotkey
                    
                    if key_name == expected_key:
                        if pressed_keys - {key_name} == expected_modifiers:
                            logger.info("检测到快捷键触发")
                            if self._callback:
                                Thread(target=self._trigger_callback, daemon=True).start()
                
            except Exception as e:
                logger.error(f"按键处理错误: {e}")
        
        def on_release_v2(key):
            try:
                if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                    pressed_keys.discard("ctrl")
                elif key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                    pressed_keys.discard("shift")
                elif key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                    pressed_keys.discard("alt")
                else:
                    try:
                        pressed_keys.discard(key.char.lower())
                    except AttributeError:
                        pass
            except Exception as e:
                logger.error(f"按键释放处理错误: {e}")
        
        with keyboard.Listener(on_press=on_press_v2, on_release=on_release_v2) as listener:
            while self._running and not self._stop_event.is_set():
                self._stop_event.wait(timeout=0.5)
            
            listener.stop()
    
    def _trigger_callback(self):
        """触发回调"""
        try:
            if self._callback:
                if asyncio.iscoroutinefunction(self._callback):
                    # 如果是异步函数，在新的事件循环中运行
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(self._callback())
                    finally:
                        loop.close()
                else:
                    self._callback()
        except Exception as e:
            logger.error(f"回调执行错误: {e}")
