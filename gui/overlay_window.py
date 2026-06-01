import tkinter as tk
import time
from typing import List, Tuple, Dict, Any, Optional

class OverlayWindow:
    """
    滑鼠穿透的透明置頂渲染視窗，用於直接在神魔之塔棋盤畫面上繪製轉珠路徑。
    """
    def __init__(self):
        self.root: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.transparent_color = "#121212"  # 指定一個極黑顏色作為透明色值
        self.path: List[Tuple[int, int]] = []
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = 0
        self.crop_h = 0
        
        # 動畫相關變數
        self.anim_dot: Optional[int] = None
        self.anim_step_idx = 0
        self.anim_running = False

    def show_path(self, path: List[Tuple[int, int]], x: int, y: int, w: int, h: int) -> None:
        """
        在指定位置顯示路徑。如果視窗未建立，會進行初始化。
        """
        self.path = path
        self.crop_x = x
        self.crop_y = y
        self.crop_w = w
        self.crop_h = h
        
        # 停止先前的動畫
        self.stop_animation()
        
        # 如果視窗已存在，則更新位置並重新繪製
        if self.root is not None and self.root.winfo_exists():
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.draw_path()
            self.start_animation()
            return
            
        # 建立全新的置頂視窗
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.config(bg=self.transparent_color)
        
        # 設定置頂屬性
        self.root.attributes("-topmost", True)
        # 設定特定顏色為 100% 透明與滑鼠穿透（Windows API）
        self.root.wm_attributes("-transparentcolor", self.transparent_color)
        
        # 建立畫布
        self.canvas = tk.Canvas(
            self.root,
            bg=self.transparent_color,
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 在 Tkinter 渲染完畢後，強制套用 Windows API 滑鼠穿透
        self.root.update_idletasks()
        from utils.win_api import make_window_click_through, make_window_topmost, get_tkinter_hwnd
        hwnd = get_tkinter_hwnd(self.root)
        if hwnd:
            make_window_click_through(hwnd)
            make_window_topmost(hwnd, True)
            
        self.draw_path()
        self.start_animation()

    def draw_path(self) -> None:
        """
        在畫布上繪製發光漸層路徑線段與步驟點。
        """
        if not self.canvas or not self.path:
            return
            
        self.canvas.delete("all")
        
        # 算出 6x5 每個單元格的尺寸
        cell_w = self.crop_w / 6.0
        cell_h = self.crop_h / 5.0
        
        # 1. 統計邊界/線段的重複穿過次數，用於邊段平行偏移 (Edge Multiplicity Offset)
        edge_visits: Dict[Tuple[Tuple[int, int], Tuple[int, int]], int] = {}
        segment_offsets = []
        
        for i in range(len(self.path) - 1):
            p1_grid = self.path[i]
            p2_grid = self.path[i+1]
            
            # 使用排序後的元組標識無向邊
            edge_key = tuple(sorted([p1_grid, p2_grid]))
            visit_count = edge_visits.get(edge_key, 0)
            edge_visits[edge_key] = visit_count + 1
            
            # 根據第幾次經過，計算偏移量 D (0, 7, -7, 14, -14 像素)
            D = 0
            if visit_count == 2:
                D = 7
            elif visit_count == 3:
                D = -7
            elif visit_count == 4:
                D = 14
            elif visit_count == 5:
                D = -14
                
            # 計算基本幾何中心座標
            cx1 = (p1_grid[1] + 0.5) * cell_w
            cy1 = (p1_grid[0] + 0.5) * cell_h
            cx2 = (p2_grid[1] + 0.5) * cell_w
            cy2 = (p2_grid[0] + 0.5) * cell_h
            
            # 計算垂直法線向量進行平移
            dx = cx2 - cx1
            dy = cy2 - cy1
            length = (dx**2 + dy**2)**0.5
            
            if length > 0 and D != 0:
                nx = -dy / length
                ny = dx / length
                # 偏移端點
                cx1_off = cx1 + nx * D
                cy1_off = cy1 + ny * D
                cx2_off = cx2 + nx * D
                cy2_off = cy2 + ny * D
            else:
                cx1_off, cy1_off = cx1, cy1
                cx2_off, cy2_off = cx2, cy2
                
            segment_offsets.append((cx1_off, cy1_off, cx2_off, cy2_off, i))

        # 2. 繪製底部黑色陰影 (帶偏移)
        shadow_offset = 1
        for x1, y1, x2, y2, i in segment_offsets:
            self.canvas.create_line(
                x1 + shadow_offset, y1 + shadow_offset,
                x2 + shadow_offset, y2 + shadow_offset,
                width=10,
                fill="#000000",
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                tags="shadow"
            )
            
        # 3. 繪製漸層彩色引導線 (帶偏移)
        total_segments = len(self.path) - 1
        for x1, y1, x2, y2, i in segment_offsets:
            ratio = i / max(1, total_segments)
            if ratio < 0.5:
                sub_ratio = ratio * 2
                r = int(0x00 * (1 - sub_ratio) + 0xff * sub_ratio)
                g = int(0xd2 * (1 - sub_ratio) + 0xea * sub_ratio)
                b = int(0xff * (1 - sub_ratio) + 0x00 * sub_ratio)
            else:
                sub_ratio = (ratio - 0.5) * 2
                r = 0xff
                g = int(0xea * (1 - sub_ratio) + 0x3f * sub_ratio)
                b = int(0x00 * (1 - sub_ratio) + 0x00 * sub_ratio)
                
            color_hex = f"#{r:02x}{g:02x}{b:02x}"
            
            self.canvas.create_line(
                x1, y1, x2, y2,
                width=6,
                fill=color_hex,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                tags="line"
            )
            
        # 4. 繪製起點特殊標記 (發光綠色同心圓)
        start_r, start_c = self.path[0]
        start_x = (start_c + 0.5) * cell_w
        start_y = (start_r + 0.5) * cell_h
        self.canvas.create_oval(
            start_x - 18, start_y - 18,
            start_x + 18, start_y + 18,
            fill="",
            outline="#2ecc71",
            width=3,
            tags="node"
        )
        self.canvas.create_oval(
            start_x - 6, start_y - 6,
            start_x + 6, start_y + 6,
            fill="#2ecc71",
            outline="",
            tags="node"
        )
        
        # 5. 繪製終點特殊標記 (發光紅色同心圓)
        end_r, end_c = self.path[-1]
        end_x = (end_c + 0.5) * cell_w
        end_y = (end_r + 0.5) * cell_h
        self.canvas.create_oval(
            end_x - 18, end_y - 18,
            end_x + 18, end_y + 18,
            fill="",
            outline="#e74c3c",
            width=3,
            tags="node"
        )
        
        # 6. 計算每個步驟點的偏置顯示，解決數字重疊問題 (Node Multiplicity Offset)
        node_visits: Dict[Tuple[int, int], int] = {}
        for idx, (r, c) in enumerate(self.path):
            visit_key = (r, c)
            k = node_visits.get(visit_key, 0)
            node_visits[visit_key] = k + 1
            
            # 根據第幾次進入這個格子，進行花瓣形散佈偏置
            label_dx, label_dy = 0, 0
            if k == 2:   # 第二次訪問，偏置到左上角
                label_dx, label_dy = -13, -13
            elif k == 3: # 第三次訪問，偏置到右下角
                label_dx, label_dy = 13, 13
            elif k == 4: # 第四次訪問，偏置到右上角
                label_dx, label_dy = 13, -13
            elif k == 5: # 第五次訪問，偏置到左下角
                label_dx, label_dy = -13, 13
            elif k >= 6: # 第六次以上訪問，偏置到正上方
                label_dx, label_dy = 0, -16

            cx = (c + 0.5) * cell_w + label_dx
            cy = (r + 0.5) * cell_h + label_dy
            
            # 每隔 3 步或起終點或明顯轉折點繪製數字
            is_bend = False
            if 0 < idx < len(self.path) - 1:
                prev_r, prev_c = self.path[idx-1]
                next_r, next_c = self.path[idx+1]
                v1 = (c - prev_c, r - prev_r)
                v2 = (next_c - c, next_r - r)
                if v1 != v2:  # 方向改變
                    is_bend = True
                    
            if idx == 0 or idx == len(self.path) - 1 or idx % 3 == 0 or is_bend:
                # 繪製圓點底圖
                circle_color = "#1e1e1e"
                if idx == 0:
                    circle_color = "#2ecc71"
                elif idx == len(self.path) - 1:
                    circle_color = "#e74c3c"
                elif k > 1:
                    circle_color = "#34495e"  # 重複訪問用藍灰色區分
                
                self.canvas.create_oval(
                    cx - 9, cy - 9,
                    cx + 9, cy + 9,
                    fill=circle_color,
                    outline="#ffffff",
                    width=1.5,
                    tags="node_label"
                )
                # 繪製白色文字步驟號
                self.canvas.create_text(
                    cx, cy,
                    text=str(idx),
                    fill="#ffffff",
                    font=("Segoe UI", 7, "bold"),
                    tags="node_label"
                )

    # --- 引導光點動畫邏輯 ---
    def start_animation(self) -> None:
        """
        啟動沿路徑流動的引導光點動畫。
        """
        if not self.canvas or len(self.path) < 2:
            return
            
        self.anim_running = True
        self.anim_step_idx = 0
        
        # 創建動畫光點 (發光粉紅/黃色圓點)
        cell_w = self.crop_w / 6.0
        cell_h = self.crop_h / 5.0
        start_r, start_c = self.path[0]
        start_x = (start_c + 0.5) * cell_w
        start_y = (start_r + 0.5) * cell_h
        
        self.anim_dot = self.canvas.create_oval(
            start_x - 10, start_y - 10,
            start_x + 10, start_y + 10,
            fill="#e84393",
            outline="#ffffff",
            width=2,
            tags="anim"
        )
        
        self.animate_step()

    def animate_step(self) -> None:
        """
        遞迴更新動畫光點的位置。
        """
        if not self.anim_running or not self.canvas or self.root is None or not self.root.winfo_exists():
            return
            
        cell_w = self.crop_w / 6.0
        cell_h = self.crop_h / 5.0
        
        self.anim_step_idx = (self.anim_step_idx + 1) % len(self.path)
        r, c = self.path[self.anim_step_idx]
        tx = (c + 0.5) * cell_w
        ty = (r + 0.5) * cell_h
        
        # 移動圓點到目標座標
        if self.anim_dot is not None:
            self.canvas.coords(
                self.anim_dot,
                tx - 9, ty - 9,
                tx + 9, ty + 9
            )
            
            # 閃爍變色增加立體科技感
            color = "#e84393" if self.anim_step_idx % 2 == 0 else "#f1c40f"
            self.canvas.itemconfig(self.anim_dot, fill=color)
        
        # 每 110 毫秒移動到下一步驟
        self.root.after(110, self.animate_step)

    def stop_animation(self) -> None:
        """
        停止當前路徑的動畫。
        """
        self.anim_running = False
        if self.canvas is not None and self.anim_dot is not None:
            try:
                self.canvas.delete("anim")
            except Exception:
                pass
            self.anim_dot = None

    def clear(self) -> None:
        """
        完全清除路徑與動畫，並隱藏/關閉視窗。
        """
        try:
            self.stop_animation()
        except Exception:
            pass
            
        if self.canvas is not None:
            try:
                self.canvas.delete("all")
            except Exception:
                pass
                
        if self.root is not None:
            try:
                if self.root.winfo_exists():
                    self.root.destroy()
            except Exception:
                pass
            self.root = None
