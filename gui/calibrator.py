import tkinter as tk
from tkinter import ttk
import json
import os
from typing import Dict, Any

class CalibratorWindow:
    """
    半透明的置頂視窗，用於讓玩家以拖曳方式精確框選遊戲畫面中的 6x5 符石區域。
    """
    def __init__(self, parent_gui: Any, config_path: str):
        self.parent_gui = parent_gui
        self.config_path = config_path
        
        # 讀取現有設定
        self.config: Dict[str, Any] = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception:
                pass
                
        # 初始化 Tkinter 子視窗
        self.root = tk.Toplevel()
        self.root.title("神魔之塔棋盤校準")
        
        # 設定為無邊框、最上層、半透明
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.6)  # 60% 透明度
        
        # 獲取上次保存的座標與大小
        self.x = self.config.get("crop_x", 100)
        self.y = self.config.get("crop_y", 400)
        self.w = self.config.get("crop_w", 400)
        self.h = self.config.get("crop_h", 333)
        self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        
        # 建立外框與內框的視覺回饋
        self.border_frame = tk.Frame(self.root, bg="#ff3333", bd=3)
        self.border_frame.pack(fill=tk.BOTH, expand=True)
        
        self.content_frame = tk.Frame(self.border_frame, bg="#2b2b2b")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 提示標籤
        self.info_label = tk.Label(
            self.content_frame,
            text="【神魔之塔 6x5 棋盤校準框】\n\n1. 拖曳此框覆蓋模擬器中的符石區域\n2. 拖曳右下角 [ ◿ ] 調整大小\n3. 確定完美覆蓋後點擊 [儲存校準]\n\n※ 請確保網格的 6x5 符石恰好都在紅色框線內",
            fg="#ffffff",
            bg="#2b2b2b",
            font=("Microsoft JhengHei", 10, "bold"),
            justify=tk.CENTER
        )
        self.info_label.pack(pady=20, padx=10, fill=tk.BOTH, expand=True)
        
        # 底部按鈕區
        self.btn_frame = tk.Frame(self.content_frame, bg="#2b2b2b")
        self.btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=15)
        
        # 儲存按鈕
        self.save_btn = tk.Button(
            self.btn_frame,
            text="儲存校準",
            command=self.save_calibration,
            bg="#2ecc71",
            fg="#ffffff",
            activebackground="#27ae60",
            activeforeground="#ffffff",
            font=("Microsoft JhengHei", 10, "bold"),
            bd=0,
            padx=15,
            pady=6,
            cursor="hand2"
        )
        self.save_btn.pack(side=tk.LEFT, expand=True, padx=20)
        
        # 取消按鈕
        self.cancel_btn = tk.Button(
            self.btn_frame,
            text="取消",
            command=self.root.destroy,
            bg="#e74c3c",
            fg="#ffffff",
            activebackground="#c0392b",
            activeforeground="#ffffff",
            font=("Microsoft JhengHei", 10, "bold"),
            bd=0,
            padx=15,
            pady=6,
            cursor="hand2"
        )
        self.cancel_btn.pack(side=tk.RIGHT, expand=True, padx=20)
        
        # 右下角縮放控制閥
        self.resize_grip = tk.Label(
            self.content_frame,
            text="◿",
            fg="#ff3333",
            bg="#2b2b2b",
            font=("Microsoft JhengHei", 14, "bold"),
            cursor="size_nw_se"
        )
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se")
        
        # 拖曳狀態變數
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_start_w = 0
        self.resize_start_h = 0
        self.resize_start_x = 0
        self.resize_start_y = 0

        # 綁定事件：滑鼠拖曳移動視窗
        self.info_label.bind("<Button-1>", self.start_drag)
        self.info_label.bind("<B1-Motion>", self.drag_window)
        self.content_frame.bind("<Button-1>", self.start_drag)
        self.content_frame.bind("<B1-Motion>", self.drag_window)
        
        # 綁定事件：右下角滑鼠拖曳縮放視窗
        self.resize_grip.bind("<Button-1>", self.start_resize)
        self.resize_grip.bind("<B1-Motion>", self.resize_window)
        
    # --- 拖曳移動視窗邏輯 ---
    def start_drag(self, event: tk.Event) -> None:
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def drag_window(self, event: tk.Event) -> None:
        deltax = event.x - self.drag_start_x
        deltay = event.y - self.drag_start_y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")
        
    # --- 拖曳縮放視窗邏輯 ---
    def start_resize(self, event: tk.Event) -> None:
        self.resize_start_w = self.root.winfo_width()
        self.resize_start_h = self.root.winfo_height()
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root

    def resize_window(self, event: tk.Event) -> None:
        dw = event.x_root - self.resize_start_x
        dh = event.y_root - self.resize_start_y
        
        # 設定最小寬高為 150x150
        new_w = max(150, self.resize_start_w + dw)
        new_h = max(150, self.resize_start_h + dh)
        
        self.root.geometry(f"{new_w}x{new_h}")
        
    # --- 儲存校準座標 ---
    def save_calibration(self) -> None:
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        
        # 更新設定檔
        self.config["crop_x"] = x
        self.config["crop_y"] = y
        self.config["crop_w"] = w
        self.config["crop_h"] = h
        
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            # 通知主 GUI 座標已更新
            if hasattr(self.parent_gui, "update_calibration_coords"):
                self.parent_gui.update_calibration_coords(x, y, w, h)
                
            print(f"校準成功已儲存: X={x}, Y={y}, W={w}, H={h}")
        except Exception as e:
            print(f"儲存校準設定失敗: {e}")
            
        self.root.destroy()
