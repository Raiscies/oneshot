"""
OneShot - 主窗口 UI
"""

import customtkinter as ctk


class MainWindow:
    """主窗口"""
    
    def __init__(self, app, services, storage_path, debug_mode=False):
        """
        初始化主窗口
        
        Args:
            app: CTk 主窗口实例
            services: 服务字典
            storage_path: 存储路径
            debug_mode: 是否启用调试模式
        """
        self.app = app
        self.services = services
        self.debug_mode = debug_mode
        self.storage_path = storage_path
        
        self._setup_ui()
        self._setup_tray()
        self._setup_shortcuts()
    
    def _setup_ui(self):
        """设置 UI"""
        self.app.title("OneShot")
        self.app.geometry("320x500")
        self.app.resizable(False, False)
        self.app.configure(fg_color="#1a1a1a")
        
        # 从配置读取快捷键
        config = self.services['config']
        hotkey_config = config.hotkey
        modifiers_list = hotkey_config.get("modifiers", ["ctrl"])
        key = hotkey_config.get("key", "q")
        
        # 构建显示字符串
        hotkey_display = "+".join(sorted(m.upper() for m in modifiers_list)) + "+" + key.upper()
        
        # 主框架（使用 ScrollableFrame 支持滚动）
        self.main_frame = ctk.CTkScrollableFrame(self.app, fg_color="#1a1a1a")
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # 快捷键显示
        self.hotkey_label = ctk.CTkLabel(
            self.main_frame, 
            text=hotkey_display, 
            font=("Consolas", 12)
        )
        self.hotkey_label.pack()
        
        # 窗口设置
        self._create_window_frame()
        
        # 快捷键设置
        self._create_shortcut_frame(modifiers_list, key)
        
        # 存储设置
        self._create_storage_frame()
        
        # 关于
        self._create_about_frame()
        
        # 调试区域（仅 debug 模式）
        self._setup_debug_frame()
    
    def _create_window_frame(self):
        """创建窗口设置区域"""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(frame, text="窗口", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        
        # 从配置读取窗口设置
        config = self.services['config']
        window_config = config.window
        
        self.always_on_top_var = ctk.BooleanVar(value=window_config.get("always_on_top", True))
        self.always_on_top_checkbox = ctk.CTkCheckBox(
            frame, 
            text="结果弹窗置顶显示",
            variable=self.always_on_top_var,
            command=self._on_always_on_top_changed
        )
        self.always_on_top_checkbox.pack(anchor="w", pady=5)
        
        self.follow_mouse_var = ctk.BooleanVar(value=window_config.get("follow_mouse", True))
        self.follow_mouse_checkbox = ctk.CTkCheckBox(
            frame, 
            text="弹窗跟随鼠标位置",
            variable=self.follow_mouse_var,
            command=self._on_follow_mouse_changed
        )
        self.follow_mouse_checkbox.pack(anchor="w", pady=5)
    
    def _on_always_on_top_changed(self):
        """置顶设置变更时更新服务"""
        self.services['ui'].set_always_on_top(self.always_on_top_var.get())
        # 保存配置
        self.services['config'].set("window", "always_on_top", self.always_on_top_var.get())
    
    def _on_follow_mouse_changed(self):
        """跟随鼠标设置变更时更新服务"""
        self.services['ui'].set_follow_mouse(self.follow_mouse_var.get())
        # 保存配置
        self.services['config'].set("window", "follow_mouse", self.follow_mouse_var.get())
    
    def _setup_debug_frame(self):
        """设置调试区域（仅在debug模式下）"""
        if self.debug_mode:
            self._create_debug_frame()
    
    def _create_shortcut_frame(self, modifiers_list, key):
        """创建快捷键设置区域"""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(frame, text="快捷键", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        
        checkbox_frame = ctk.CTkFrame(frame)
        checkbox_frame.pack(fill="x", pady=5)
        
        # 从配置初始化复选框状态
        self.ctrl_var = ctk.BooleanVar(value="ctrl" in modifiers_list)
        self.shift_var = ctk.BooleanVar(value="shift" in modifiers_list)
        self.alt_var = ctk.BooleanVar(value="alt" in modifiers_list)
        
        ctk.CTkCheckBox(checkbox_frame, text="Ctrl", variable=self.ctrl_var).pack(side="left", padx=5)
        ctk.CTkCheckBox(checkbox_frame, text="Shift", variable=self.shift_var).pack(side="left", padx=5)
        ctk.CTkCheckBox(checkbox_frame, text="Alt", variable=self.alt_var).pack(side="left", padx=5)
        
        self.key_option = ctk.CTkOptionMenu(frame, values=["Q", "L", "K", "J"], width=80)
        self.key_option.pack(anchor="w", pady=5)
        self.key_option.set(key.upper())
        
        ctk.CTkButton(frame, text="应用快捷键", width=150, command=self._apply_hotkey).pack(anchor="w", pady=5)
        
        # 绑定更新事件
        self.ctrl_var.trace_add("write", lambda *_: self._update_hotkey_display())
        self.shift_var.trace_add("write", lambda *_: self._update_hotkey_display())
        self.alt_var.trace_add("write", lambda *_: self._update_hotkey_display())
        self.key_option.configure(command=lambda _: self._update_hotkey_display())
    
    def _update_hotkey_display(self):
        """更新快捷键显示"""
        modifiers = []
        if self.ctrl_var.get():
            modifiers.append("Ctrl")
        if self.shift_var.get():
            modifiers.append("Shift")
        if self.alt_var.get():
            modifiers.append("Alt")
        
        self.hotkey_label.configure(text="+".join(modifiers) + "+" + self.key_option.get())
    
    def _apply_hotkey(self):
        """应用快捷键设置"""
        modifiers = {"ctrl" if self.ctrl_var.get() else "", 
                    "shift" if self.shift_var.get() else "", 
                    "alt" if self.alt_var.get() else ""}.difference({""})
        key = self.key_option.get().lower()
        
        # 更新实际快捷键
        self.services['keyboard'].set_hotkey(
            self.services.get('hotkey_callback'),
            modifiers,
            key
        )
        
        # 保存到配置并持久化
        self.services['config'].set("hotkey", "modifiers", list(modifiers))
        self.services['config'].set("hotkey", "key", key)
        self.services['config'].save()
        
        # 更新显示
        hotkey_display = "+".join(sorted(m.upper() for m in modifiers)) + "+" + key.upper()
        self.hotkey_label.configure(text=hotkey_display)
    
    def _create_storage_frame(self):
        """创建存储设置区域"""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(frame, text="存储", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        
        self.path_entry = ctk.CTkEntry(frame, width=200)
        self.path_entry.insert(0, self.storage_path)
        self.path_entry.pack(fill="x", pady=5)
        
        ctk.CTkButton(frame, text="打开目录", command=self._open_folder).pack(anchor="w")
    
    def _create_about_frame(self):
        """创建关于区域"""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(frame, text="关于", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(frame, text="一键直达文献").pack(anchor="w")
        ctk.CTkLabel(frame, text="版本: 0.1.0", text_color="gray").pack(anchor="w")
    
    def _create_debug_frame(self):
        """创建调试区域"""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=10, padx=5)
        
        ctk.CTkLabel(
            frame, 
            text="调试区", 
            font=ctk.CTkFont(weight="bold", size=14), 
            text_color="red"
        ).pack(anchor="w")
        
        ctk.CTkButton(frame, text="测试弹窗", command=self._show_test_dialog).pack(anchor="w")
    
    def _open_folder(self):
        """打开存储目录"""
        import os
        path = os.path.abspath(self.path_entry.get())
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        os.startfile(path)
    
    def _show_test_dialog(self):
        """显示测试弹窗"""
        import pyautogui
        from oneshot.models import Paper
        
        test_papers = [
            Paper(
                title="simpler hierarchical routing in road networks",
                authors=["Robert Geisberger", "Peter Sanders", "Dominik Schultes", "Daniel Delling"],
                year=2008,
                abstract='''We present a route planning technique solely based on the concept of node contraction. The nodes are first ordered by 'importance'. A hierarchy is then generated by iteratively contracting the least important node. Contracting a node v means replacing shortest paths going through v by shortcuts. We obtain a hierarchical query algorithm using bidirectional shortest-path search. The forward search uses only edges leading to more important nodes and the backward search uses only edges coming from more important nodes. For fastest routes in road networks, the graph remains very sparse throughout the contraction process using rather simple heuristics for ordering the nodes. We have five times lower query times than the best previous hierarchical Dijkstra-based speedup techniques and a negative space overhead, i.e., the data structure for distance computation needs less space than the input graph. CHs can be combined with many other route planning techniques, leading to improved performance for many-to-many routing, transit-node routing, goal-directed routing or mobile and dynamic scenarios.
                '''
            ),
            Paper(
                title="Data structures for categorical path counting queries",
                authors=["Meng He", "Serikzhan Kazi"],
                year=2022,
                abstract='''Consider an ordinal tree T on n nodes, each of which is assigned a category from an alphabet. We preprocess the tree T in order to support categorical path counting queries, which ask for the number of distinct categories occurring on the path in T between two query nodes x and y.'''
            ),
        ]
        
        test_captured_text = '''[19] Robert Geisberger, Peter Sanders, Dominik Schultes, and Daniel Delling. 2008. Contraction hierarchies: Faster and simpler hierarchical routing in road networks. In International workshop on experimental and efficient algorithms. 319–333.'''
        
        self.services['ui'].show(test_papers, captured_text=test_captured_text)
    
    def _setup_tray(self):
        """设置托盘"""
        # 从配置读取快捷键显示
        config = self.services['config']
        hotkey_config = config.hotkey
        modifiers_list = hotkey_config.get("modifiers", ["ctrl"])
        key = hotkey_config.get("key", "q")
        hotkey_display = "+".join(sorted(m.upper() for m in modifiers_list)) + "+" + key.upper()
        self.services['tray'].notify("OneShot", f"程序已启动，按 {hotkey_display} 触发")
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        pass  # 在外部设置回调
    
    def on_closing(self):
        """关闭窗口时最小化到托盘"""
        # 保存配置
        self.services['config'].save()
        
        # 从配置读取快捷键显示
        config = self.services['config']
        hotkey_config = config.hotkey
        modifiers_list = hotkey_config.get("modifiers", ["ctrl"])
        key = hotkey_config.get("key", "q")
        hotkey_display = "+".join(sorted(m.upper() for m in modifiers_list)) + "+" + key.upper()
        
        self.app.withdraw()
        self.services['tray'].notify("OneShot", f"程序已在后台运行，按 {hotkey_display} 触发")
    
    def show(self):
        """显示窗口"""
        self.app.deiconify()
        self.app.state("normal")