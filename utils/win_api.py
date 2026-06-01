import win32gui
import win32con
import ctypes
from typing import Any

def make_window_click_through(hwnd: int) -> bool:
    """
    設定 Windows 視窗為滑鼠穿透與分層樣式。
    這允許玩家點擊該視窗時，點擊事件會直接穿透到下方的遊戲模擬器。
    """
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        # WS_EX_TRANSPARENT: 滑鼠穿透
        # WS_EX_LAYERED: 支援透明分層
        new_style = style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
        return True
    except Exception as e:
        print(f"設定滑鼠穿透失敗: {e}")
        return False


def make_window_topmost(hwnd: int, topmost: bool = True) -> bool:
    """
    設定視窗置頂。
    """
    try:
        flags = win32con.SWP_NOSIZE | win32con.SWP_NOMOVE
        insert_after = win32con.HWND_TOPMOST if topmost else win32con.HWND_NOTOPMOST
        win32gui.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags)
        return True
    except Exception as e:
        print(f"設定視窗置頂失敗: {e}")
        return False


def get_tkinter_hwnd(widget: Any) -> int:
    """
    獲取 Tkinter 元件的原生 Windows HWND 控點。
    """
    try:
        widget.update_idletasks()
        hwnd = win32gui.GetParent(widget.winfo_id())
        if hwnd == 0:
            hwnd = widget.winfo_id()
        return hwnd
    except Exception:
        try:
            return int(widget.wm_frame(), 16)
        except Exception:
            return 0


def set_timer_resolution(resolution_ms: int = 1) -> bool:
    """
    提升 Windows 執行緒排程器精度（通常為 1ms），使 time.sleep() 支援亞毫秒級別的精準喚醒。
    這在極速轉珠微步拖曳中極為重要，可避免 Windows 預設 15.6ms 帶來的卡頓。
    """
    try:
        ctypes.windll.winmm.timeBeginPeriod(resolution_ms)
        return True
    except Exception as e:
        print(f"設定高精度定時器失敗: {e}")
        return False


def reset_timer_resolution(resolution_ms: int = 1) -> bool:
    """
    恢復 Windows 執行緒排程器的預設精度限制。
    """
    try:
        ctypes.windll.winmm.timeEndPeriod(resolution_ms)
        return True
    except Exception as e:
        print(f"重設高精度定時器失敗: {e}")
        return False
