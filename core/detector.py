import numpy as np
import cv2
from typing import List, Tuple, Dict

class OrbDetector:
    """
    分析神魔之塔 6x5 棋盤畫面並辨識出每個單元格中的符石屬性。
    符石代號：
    - 0: 水 (Water) - 藍色
    - 1: 火 (Fire) - 紅色
    - 2: 木 (Earth) - 綠色
    - 3: 光 (Light) - 黃色
    - 4: 暗 (Dark) - 紫色
    - 5: 心 (Heart) - 粉紅色
    """
    def __init__(self):
        # 符石代號與名稱、顏色的對照表
        self.orb_names: Dict[int, str] = {
            0: "水",
            1: "火",
            2: "木",
            3: "光",
            4: "暗",
            5: "心"
        }
        self.orb_symbols: Dict[int, str] = {
            0: "💧",
            1: "🔥",
            2: "🍃",
            3: "✨",
            4: "😈",
            5: "❤️"
        }
        self.orb_colors: Dict[int, str] = {
            0: "#3498db",  # 藍
            1: "#e74c3c",  # 紅
            2: "#2ecc71",  # 綠
            3: "#f1c40f",  # 黃
            4: "#9b59b6",  # 紫
            5: "#e84393"   # 粉
        }

        # 定義 6 種符石標準色的 LAB 中心點 (L: 0~100, a: -127~127, b: -127~127)
        self.reference_lab = {
            0: np.array([60.0, -1.3, -48.3]),   # 水
            1: np.array([51.0, 66.9, 44.3]),    # 火
            2: np.array([71.4, -59.9, 39.0]),   # 木
            3: np.array([86.8, -10.0, 78.3]),   # 光
            4: np.array([42.6, 63.8, -58.9]),   # 暗
            5: np.array([61.4, 58.4, 0.3])      # 心
        }

    def _bgr_to_lab(self, b: float, g: float, r: float) -> np.ndarray:
        """
        將單一 BGR 顏色轉換為 CIELAB 顏色空間。
        """
        pixel = np.array([[[b, g, r]]], dtype=np.float32) / 255.0
        return cv2.cvtColor(pixel, cv2.COLOR_BGR2LAB)[0][0]

    def identify_orb(self, r: int, g: int, b: int) -> int:
        """
        根據平均 RGB 值，精準辨識符石類型。
        """
        orb_type, _confidence = self.classify_orb(r, g, b)
        return orb_type

    def classify_orb(self, r: int, g: int, b: int) -> Tuple[int, float]:
        """
        使用 CIELAB 顏色空間的最鄰近演算法辨識符石。
        """
        lab = self._bgr_to_lab(float(b), float(g), float(r))
        
        min_dist = float('inf')
        best_orb = -1
        
        for orb_type, ref_lab in self.reference_lab.items():
            dist = np.linalg.norm(lab - ref_lab)
            if dist < min_dist:
                min_dist = dist
                best_orb = orb_type
                
        # 計算信心值：距離越小，信心值越高。最大容忍距離約為 80。
        confidence = max(0.0, 1.0 - (min_dist / 80.0))
        return best_orb, round(float(confidence), 3)

    def detect_obstacle(self, r_mean: float, g_mean: float, b_mean: float, r_std: float, g_std: float, b_std: float) -> int:
        """
        根據顏色的平均值與標準差，初步判斷是否有障礙物覆蓋。
        目前回傳值定義：
        0: 無障礙物
        1: 風化珠 (Weathered) - 尚未有精確特徵，預留擴充
        """
        avg_std = (r_std + g_std + b_std) / 3.0
        max_mean = max(r_mean, g_mean, b_mean)
        min_mean = min(r_mean, g_mean, b_mean)
        if max_mean < 35:
            return 1
        if avg_std > 75 and (max_mean - min_mean) < 45:
            return 1
        return 0

    def detect_board(self, board_img: np.ndarray) -> Tuple[List[List[int]], List[List[int]], List[List[float]]]:
        """
        分析裁切出來的棋盤圖像(numpy BGR array)，辨識 6x5 網格內的符石與障礙物狀態。
        """
        img_h, img_w = board_img.shape[:2]
        
        cell_w = img_w / 6.0
        cell_h = img_h / 5.0
        
        board_grid: List[List[int]] = []
        obstacle_grid: List[List[int]] = []
        confidence_grid: List[List[float]] = []
        
        for r in range(5):
            row_orbs: List[int] = []
            row_obs: List[int] = []
            row_conf: List[float] = []
            for c in range(6):
                # 計算該單元格的範圍
                x1 = int(c * cell_w)
                y1 = int(r * cell_h)
                x2 = int((c + 1) * cell_w)
                y2 = int((r + 1) * cell_h)
                
                # 擷取中心 60% 區域以避開反光與邊界
                w_cell = x2 - x1
                h_cell = y2 - y1
                cx1 = x1 + int(w_cell * 0.2)
                cx2 = x1 + int(w_cell * 0.8)
                cy1 = y1 + int(h_cell * 0.2)
                cy2 = y1 + int(h_cell * 0.8)
                
                center_pixels = board_img[cy1:cy2, cx1:cx2]
                
                # 計算該區塊像素的平均值與標準差 (axis=(0,1) 即高與寬)
                # BGR 格式
                means = np.median(center_pixels.reshape(-1, 3), axis=0)
                stds = center_pixels.std(axis=(0, 1))
                
                b_mean, g_mean, r_mean = means
                b_std, g_std, r_std = stds
                
                orb_type, confidence = self.classify_orb(int(r_mean), int(g_mean), int(b_mean))
                obs_type = self.detect_obstacle(r_mean, g_mean, b_mean, r_std, g_std, b_std)
                
                row_orbs.append(orb_type)
                row_obs.append(obs_type)
                row_conf.append(round(float(confidence), 3))
                
            board_grid.append(row_orbs)
            obstacle_grid.append(row_obs)
            confidence_grid.append(row_conf)
            
        return board_grid, obstacle_grid, confidence_grid

    def print_board_text(self, grid: List[List[int]]) -> str:
        """
        在控制台以 Emoji 視覺化方式打印棋盤，用於偵錯。
        """
        lines: List[str] = []
        for row in grid:
            line = " ".join([self.orb_symbols.get(orb, "?") for orb in row])
            lines.append(line)
        return "\n".join(lines)
