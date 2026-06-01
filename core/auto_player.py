import ctypes
import time
import math
import random
from typing import List, Tuple
from utils.win_api import set_timer_resolution, reset_timer_resolution

# Windows API 常數定義
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

# Windows API 結構體定義
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("ii", _INPUT),
    ]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_mouse_pos() -> Tuple[int, int]:
    """取得當前滑鼠在螢幕上的物理像素座標。"""
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _screen_size() -> Tuple[int, int]:
    """取得主螢幕解析度。"""
    user32 = ctypes.windll.user32
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return w, h


def _to_absolute(x: int, y: int) -> Tuple[int, int]:
    """將螢幕像素座標轉換為 Windows SendInput 所需的 65535 歸一化座標。"""
    sw, sh = _screen_size()
    abs_x = int(x * 65535 / sw)
    abs_y = int(y * 65535 / sh)
    return abs_x, abs_y


def _send_input(flags: int, x: int = 0, y: int = 0) -> None:
    """低階 SendInput 發送滑鼠事件。"""
    abs_x, abs_y = _to_absolute(x, y)
    mi = MOUSEINPUT(
        dx=abs_x,
        dy=abs_y,
        mouseData=0,
        dwFlags=flags,
        time=0,
        dwExtraInfo=ctypes.pointer(ctypes.c_ulong(0)),
    )
    inp = INPUT(type=INPUT_MOUSE)
    inp.ii.mi = mi
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def spin_sleep(duration_s: float) -> None:
    """
    使用自旋鎖 (Spin-wait) 提供精準的高解析度延遲，避免 time.sleep 在 Windows 上的毫秒級誤差。
    """
    if duration_s <= 0:
        return
    # 對於超過 2 毫秒的延遲，先用 time.sleep 釋放 CPU 資源
    if duration_s > 0.002:
        time.sleep(duration_s - 0.0015)
    
    target_time = time.perf_counter() + duration_s
    while time.perf_counter() < target_time:
        pass


def ease_in_out_sine(t: float) -> float:
    """平滑的弦波緩動函數，用於模擬手指加速減速"""
    return -(math.cos(math.pi * t) - 1) / 2


class AutoPlayer:
    """
    自動轉珠器：根據計算好的路徑在模擬器畫面上自動執行滑鼠拖曳操作。
    使用 Windows SendInput API 確保與各款 Android 模擬器的最大相容性。
    引入 Bézier 微小抖動與 Spin-wait 亞毫秒精準控制防外掛偵測。
    """
    def __init__(self, move_delay_ms: int = 45, start_delay_ms: int = 300, human_move_threshold: int = 30):
        self.move_delay_ms = move_delay_ms
        self.start_delay_ms = start_delay_ms
        self.human_move_threshold = human_move_threshold
        self.is_running = False

    def play(
        self,
        path: List[Tuple[int, int]],
        crop_x: int,
        crop_y: int,
        crop_w: int,
        crop_h: int,
    ) -> bool:
        if not path or len(path) < 2:
            print("路徑太短，無法執行自動轉珠。")
            return False

        self.is_running = True
        cell_w = crop_w / 6.0
        cell_h = crop_h / 5.0

        def grid_to_screen(r: int, c: int) -> Tuple[int, int]:
            sx = int(crop_x + (c + 0.5) * cell_w)
            sy = int(crop_y + (r + 0.5) * cell_h)
            return sx, sy

        set_timer_resolution(1)
        try:
            # 1. 移動到起點
            start_r, start_c = path[0]
            sx, sy = grid_to_screen(start_r, start_c)
            _send_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, sx, sy)
            time.sleep(0.05)
            
            expected_x, expected_y = sx, sy

            # 2. 按下滑鼠左鍵（拿起符石）
            _send_input(MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, sx, sy)
            print(f"[起手階段] 按下滑鼠，預期座標: ({sx}, {sy})，將等待 {self.start_delay_ms}ms")
            
            start_time = time.time()
            check_interval = 0.05
            last_check_time = start_time
            
            while (time.time() - start_time) * 1000 < self.start_delay_ms:
                current_time = time.time()
                if (current_time - last_check_time) >= check_interval:
                    cx, cy = get_mouse_pos()
                    if abs(cx - expected_x) > self.human_move_threshold or abs(cy - expected_y) > self.human_move_threshold:
                        self.stop()
                        return False
                    last_check_time = current_time
                time.sleep(0.01)

            # 3. 沿路徑逐格拖曳
            for i in range(1, len(path)):
                if not self.is_running:
                    break

                r, c = path[i]
                tx, ty = grid_to_screen(r, c)

                prev_r, prev_c = path[i - 1]
                px, py = grid_to_screen(prev_r, prev_c)
                
                # 步數：基於距離與速度計算
                steps = 8
                step_duration = (self.move_delay_ms / 1000.0) / steps
                
                # 引入輕微控制點，形成二次貝茲曲線的控制點 (加入隨機抖動 Jitter)
                jitter_x = random.randint(-5, 5)
                jitter_y = random.randint(-5, 5)
                ctrl_x = (px + tx) / 2 + jitter_x
                ctrl_y = (py + ty) / 2 + jitter_y

                for s in range(1, steps + 1):
                    if not self.is_running:
                        break
                        
                    # --- 滑鼠人為移動檢測 ---
                    cx, cy = get_mouse_pos()
                    if abs(cx - expected_x) > self.human_move_threshold or abs(cy - expected_y) > self.human_move_threshold:
                        self.stop()
                        return False

                    t = s / steps
                    # Ease-in-out 控制速度
                    eased_t = ease_in_out_sine(t)
                    
                    # 二次貝茲曲線公式
                    ix = int((1 - eased_t)**2 * px + 2 * (1 - eased_t) * eased_t * ctrl_x + eased_t**2 * tx)
                    iy = int((1 - eased_t)**2 * py + 2 * (1 - eased_t) * eased_t * ctrl_y + eased_t**2 * ty)
                    
                    _send_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, ix, iy)
                    
                    # 使用 Spin-wait 高精度等待
                    spin_sleep(step_duration)
                    
                    expected_x, expected_y = ix, iy

                if not self.is_running:
                    break

                # 到達格子中心後短暫停頓
                spin_sleep(0.005)

            # 4. 放開滑鼠左鍵
            last_r, last_c = path[-1]
            ex, ey = grid_to_screen(last_r, last_c)
            _send_input(MOUSEEVENTF_LEFTUP | MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, ex, ey)
            print(f"✅ 自動轉珠完成！共移動 {len(path) - 1} 步。")
            return True

        except Exception as e:
            try:
                _send_input(MOUSEEVENTF_LEFTUP, 0, 0)
            except Exception:
                pass
            print(f"自動轉珠發生錯誤: {e}")
            return False
        finally:
            self.is_running = False
            reset_timer_resolution(1)

    def stop(self) -> None:
        self.is_running = False
        try:
            cx, cy = get_mouse_pos()
            _send_input(MOUSEEVENTF_LEFTUP | MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, cx, cy)
        except Exception:
            pass
        print("自動轉珠已中斷。")
