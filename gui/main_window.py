import customtkinter as ctk
import tkinter as tk
import json
import os
from typing import Dict, Any, Optional, List, Tuple

from gui.calibrator import CalibratorWindow
from gui.overlay_window import OverlayWindow
from core.controller import BotController

class MainWindow:
    """
    神魔之塔轉珠助手 - 主控制面板 GUI (採用 CustomTkinter 打造極致科技深色主題)
    """
    def __init__(self, config_path: str, controller: BotController):
        self.config_path = config_path
        self.controller = controller
        self.overlay = OverlayWindow()
        
        # 讀取設定檔
        self.config = self.load_config()
        self.controller.update_config(self.config)
        
        self.controller.on_board_detected = lambda grid, obs=None, conf=None: self.root.after(0, self.draw_board_preview, grid, obs, conf)
        self.controller.on_path_solved = lambda path: self.root.after(0, self.draw_path_overlay, path)
        self.controller.on_auto_trigger_disabled = lambda: self.root.after(0, self.disable_auto_trigger)
        self.controller.on_clear_path = lambda: self.root.after(0, self.overlay.clear)
        
        # 初始化 CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("TOS Solver - 神魔轉珠助手 PRO")
        self.root.geometry("500x740")
        self.root.resizable(False, False)
        
        self.create_widgets()
        self.update_calibration_display()

    def load_config(self) -> Dict[str, Any]:
        default_config: Dict[str, Any] = {
            "crop_x": 100, "crop_y": 400, "crop_w": 400, "crop_h": 333,
            "max_steps": 45, "beam_width": 200, "solve_mode": "max_combo",
            "move_delay_ms": 45, "start_delay_ms": 300,
            "mouse_move_threshold": 30, "auto_trigger": 0, "auto_interval_s": 1.0,
            "min_confidence": 0.45, "max_low_confidence_cells": 2, "allow_obstacles": 1,
            "target_combo": 8
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return {k: config.get(k, default_config[k]) for k in default_config}
            except Exception:
                return default_config
        return default_config

    def save_config(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.controller.update_config(self.config)
        except Exception as e:
            print(f"儲存設定檔失敗: {e}")

    def create_widgets(self) -> None:
        # --- 頂部標題區 ---
        title_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        title_frame.pack(fill=ctk.X, padx=20, pady=(20, 10))
        
        ctk.CTkLabel(title_frame, text="神魔之塔 轉珠助手", font=("Microsoft JhengHei", 24, "bold"), text_color="#00d2ff").pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Ultimate Auto Solver & Overlay Helper", font=("Segoe UI", 12), text_color="#7f8c8d").pack(anchor="w")

        # --- 核心卡片容器 1：棋盤校準區 ---
        calib_card = ctk.CTkFrame(self.root, corner_radius=10)
        calib_card.pack(fill=ctk.X, padx=20, pady=10)
        
        c_title = ctk.CTkLabel(calib_card, text="1. 棋盤範圍校準 (Calibration)", font=("Microsoft JhengHei", 14, "bold"))
        c_title.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))
        
        self.coords_lbl = ctk.CTkLabel(calib_card, text="目前座標：未校準", font=("Microsoft JhengHei", 12), text_color="#bdc3c7")
        self.coords_lbl.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 10))
        
        calib_btn = ctk.CTkButton(calib_card, text="開始校準框選", command=self.open_calibrator, font=("Microsoft JhengHei", 12, "bold"), fg_color="#00d2ff", text_color="#1a1a1f", hover_color="#00b4db", width=120)
        calib_btn.grid(row=1, column=1, sticky="e", padx=15, pady=(0, 10))
        calib_card.grid_columnconfigure(0, weight=1)

        # --- 核心卡片容器 2：轉珠參數設定區 ---
        settings_card = ctk.CTkFrame(self.root, corner_radius=10)
        settings_card.pack(fill=ctk.X, padx=20, pady=10)
        
        s_title = ctk.CTkLabel(settings_card, text="2. 演算法與策略設定 (Settings)", font=("Microsoft JhengHei", 14, "bold"))
        s_title.grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(10, 10))
        
        def create_entry(row, col_start, label_text, key):
            ctk.CTkLabel(settings_card, text=label_text, font=("Microsoft JhengHei", 12)).grid(row=row, column=col_start, sticky="w", padx=(15, 5), pady=5)
            var = tk.StringVar(value=str(self.config.get(key, "")))
            entry = ctk.CTkEntry(settings_card, textvariable=var, width=70, justify="center")
            entry.grid(row=row, column=col_start + 1, sticky="e", padx=(5, 15), pady=5)
            entry.bind("<FocusOut>", lambda e: self.on_settings_change())
            return var
            
        self.steps_var = create_entry(1, 0, "路徑步數:", "max_steps")
        self.beam_var = create_entry(1, 2, "搜尋寬度:", "beam_width")
        
        self.move_delay_var = create_entry(2, 0, "轉珠速度(ms):", "move_delay_ms")
        self.start_delay_var = create_entry(2, 2, "起手延遲(ms):", "start_delay_ms")
        
        self.interval_var = create_entry(3, 0, "辨識間隔(秒):", "auto_interval_s")

        # 自動起手開關
        ctk.CTkLabel(settings_card, text="自動起手:", font=("Microsoft JhengHei", 12)).grid(row=3, column=2, sticky="w", padx=(15, 5), pady=5)
        self.auto_trigger_switch = ctk.CTkSwitch(
            settings_card, text="", command=self.on_auto_trigger_toggle,
            onvalue=1, offvalue=0, progress_color="#2ecc71"
        )
        self.auto_trigger_switch.grid(row=3, column=3, sticky="e", padx=(5, 15), pady=5)
        if self.config.get("auto_trigger", 0) == 1:
            self.auto_trigger_switch.select()
        else:
            self.auto_trigger_switch.deselect()

        # 轉珠策略下拉選單 (Row 4)
        ctk.CTkLabel(settings_card, text="轉珠策略:", font=("Microsoft JhengHei", 12)).grid(row=4, column=0, sticky="w", padx=(15, 5), pady=(5, 10))
        self.strategy_map = {
            "最大 Combo": "max_combo",
            "首消全版": "full_board",
            "至少指定 Combo": "at_least_c",
            "剛好指定 Combo": "exactly_c"
        }
        self.strategy_rev_map = {v: k for k, v in self.strategy_map.items()}
        current_strategy = self.config.get("solve_mode", "max_combo")
        current_strategy_display = self.strategy_rev_map.get(current_strategy, "最大 Combo")
        
        self.strategy_menu = ctk.CTkOptionMenu(
            settings_card,
            values=list(self.strategy_map.keys()),
            command=self.on_strategy_change,
            width=110
        )
        self.strategy_menu.set(current_strategy_display)
        self.strategy_menu.grid(row=4, column=1, sticky="e", padx=(5, 15), pady=(5, 10))

        # 目標 Combo 數選擇 (Row 4)
        self.target_combo_lbl = ctk.CTkLabel(settings_card, text="目標 Combo:", font=("Microsoft JhengHei", 12))
        self.target_combo_lbl.grid(row=4, column=2, sticky="w", padx=(15, 5), pady=(5, 10))
        
        self.target_combo_menu = ctk.CTkOptionMenu(
            settings_card,
            values=[str(i) for i in range(1, 11)],
            command=self.on_target_combo_change,
            width=70
        )
        self.target_combo_menu.set(str(self.config.get("target_combo", 8)))
        self.target_combo_menu.grid(row=4, column=3, sticky="e", padx=(5, 15), pady=(5, 10))
        
        # 根據目前的策略更新目標 Combo 欄位狀態
        self.update_target_combo_state(current_strategy)

        settings_card.grid_columnconfigure(0, weight=1)
        settings_card.grid_columnconfigure(1, weight=1)
        settings_card.grid_columnconfigure(2, weight=1)
        settings_card.grid_columnconfigure(3, weight=1)

        # --- 核心卡片容器 3：即時辨識預覽棋盤 ---
        preview_card = ctk.CTkFrame(self.root, corner_radius=10)
        preview_card.pack(fill=ctk.BOTH, expand=True, padx=20, pady=10)
        
        p_title = ctk.CTkLabel(preview_card, text="3. 符石辨識結果預覽 (Preview)", font=("Microsoft JhengHei", 14, "bold"))
        p_title.pack(anchor="w", padx=15, pady=(10, 5))
        
        self.preview_canvas = tk.Canvas(
            preview_card, bg="#1a1a1f", highlightthickness=1, highlightbackground="#34495e"
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # 等待畫布準備好再畫空網格
        self.root.after(100, self.draw_empty_preview)

        # --- 底部熱鍵引導提示區 ---
        tip_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        tip_frame.pack(fill=ctk.X, padx=20, pady=(0, 10))
        
        hotkeys_text = "【快捷鍵指引】\nF1：辨識並求解   F2：清除路徑   F3：手動預覽\nF4：全自動轉珠   F5：緊急停止"
        ctk.CTkLabel(tip_frame, text=hotkeys_text, font=("Microsoft JhengHei", 11), text_color="#7f8c8d", justify=tk.LEFT).pack(side=tk.LEFT)

    def draw_empty_preview(self) -> None:
        self.preview_canvas.delete("all")
        self.preview_canvas.update()
        w = self.preview_canvas.winfo_width()
        h = self.preview_canvas.winfo_height()
        if w < 10: w = 390
        if h < 10: h = 135
        
        self.preview_canvas.create_text(
            w / 2.0, h / 2.0,
            text="尚未辨識棋盤\n請按 [F3] 預覽或 [F1] 開始求解",
            fill="#7f8c8d", font=("Microsoft JhengHei", 10), justify=tk.CENTER
        )

    def draw_board_preview(
        self,
        grid: List[List[int]],
        obstacle_grid: Optional[List[List[int]]] = None,
        confidence_grid: Optional[List[List[float]]] = None,
    ) -> None:
        self.preview_canvas.delete("all")
        self.preview_canvas.update()
        w = self.preview_canvas.winfo_width()
        h = self.preview_canvas.winfo_height()
        
        rows, cols = 5, 6
        cell_w = w / cols
        cell_h = h / rows
        radius = min(cell_w, cell_h) * 0.35
        
        for r in range(rows):
            for c in range(cols):
                orb_type = grid[r][c]
                obs_type = obstacle_grid[r][c] if obstacle_grid else 0
                confidence = confidence_grid[r][c] if confidence_grid else 1.0
                
                color = self.controller.detector.orb_colors.get(orb_type, "#7f8c8d")
                symbol = self.controller.detector.orb_names.get(orb_type, "")
                
                cx = (c + 0.5) * cell_w
                cy = (r + 0.5) * cell_h
                
                self.preview_canvas.create_oval(
                    cx - radius, cy - radius, cx + radius, cy + radius,
                    fill=color,
                    outline="#ff3b30" if obs_type else ("#f1c40f" if confidence < 0.45 else "#ffffff"),
                    width=3 if obs_type or confidence < 0.45 else 1
                )
                
                self.preview_canvas.create_text(
                    cx, cy, text=symbol,
                    fill="#ffffff" if orb_type != 3 else "#1a1a1f",
                    font=("Microsoft JhengHei", 9, "bold")
                )
                if confidence < 0.45:
                    self.preview_canvas.create_text(
                        cx, cy + radius + 8,
                        text=f"{confidence:.2f}",
                        fill="#f1c40f",
                        font=("Segoe UI", 7, "bold")
                    )

    def draw_path_overlay(self, path: List[Tuple[int, int]]) -> None:
        x = self.config.get("crop_x", 0)
        y = self.config.get("crop_y", 0)
        w = self.config.get("crop_w", 0)
        h = self.config.get("crop_h", 0)
        self.overlay.show_path(path, x, y, w, h)

    def open_calibrator(self) -> None:
        CalibratorWindow(self, self.config_path)

    def update_calibration_coords(self, x: int, y: int, w: int, h: int) -> None:
        self.config["crop_x"], self.config["crop_y"] = x, y
        self.config["crop_w"], self.config["crop_h"] = w, h
        self.save_config()
        self.update_calibration_display()

    def update_calibration_display(self) -> None:
        x = self.config.get("crop_x", 0)
        y = self.config.get("crop_y", 0)
        w = self.config.get("crop_w", 0)
        h = self.config.get("crop_h", 0)
        self.coords_lbl.configure(text=f"目前座標：X={x}, Y={y} | 大小={w}x{h}", text_color="#2ecc71")

    def on_settings_change(self) -> None:
        try:
            self.config["max_steps"] = max(10, min(200, int(self.steps_var.get())))
            self.config["beam_width"] = max(10, min(2000, int(self.beam_var.get())))
            self.config["auto_interval_s"] = max(0.05, min(10.0, float(self.interval_var.get())))
            self.config["move_delay_ms"] = max(1, min(2000, int(self.move_delay_var.get())))
            self.config["start_delay_ms"] = max(10, min(2000, int(self.start_delay_var.get())))
            self.save_config()
        except ValueError:
            pass

    def on_auto_trigger_toggle(self) -> None:
        val = self.auto_trigger_switch.get()
        self.config["auto_trigger"] = val
        self.save_config()
        self.controller.last_scan_grid = None
        self.controller.last_played_grid = None
        print(f"自動起手功能已變更為: {'開啟' if val == 1 else '關閉'}")

    def disable_auto_trigger(self) -> None:
        self.config["auto_trigger"] = 0
        self.auto_trigger_switch.deselect()
        self.save_config()
        self.controller.last_scan_grid = None
        self.controller.last_played_grid = None
        self.controller.auto_player.stop()
        self.overlay.clear()

    # 熱鍵觸發由外部 main 呼叫，轉發至 controller
    def trigger_solve(self): self.controller.enqueue_task('solve')
    def trigger_clear(self): self.overlay.clear()
    def trigger_detection(self): self.controller.enqueue_task('detect')
    def trigger_auto_play(self): self.controller.enqueue_task('auto_play')
    def trigger_stop_auto(self): 
        self.controller.auto_player.stop()
        self.overlay.clear()

    def on_strategy_change(self, selected_display: str) -> None:
        strategy_key = self.strategy_map.get(selected_display, "max_combo")
        self.config["solve_mode"] = strategy_key
        self.save_config()
        self.update_target_combo_state(strategy_key)
        
    def on_target_combo_change(self, selected_val: str) -> None:
        try:
            self.config["target_combo"] = int(selected_val)
            self.save_config()
        except ValueError:
            pass
            
    def update_target_combo_state(self, strategy: str) -> None:
        if strategy in ("at_least_c", "exactly_c"):
            self.target_combo_lbl.configure(text_color="#ffffff")
            self.target_combo_menu.configure(state="normal")
        else:
            self.target_combo_lbl.configure(text_color="#555555")
            self.target_combo_menu.configure(state="disabled")

    def run(self) -> None:
        self.root.mainloop()

    def cleanup(self) -> None:
        self.save_config()
        self.controller.stop()
        self.overlay.clear()
