import mss
import numpy as np
from typing import Optional

class ScreenCapturer:
    """
    使用 mss 庫進行極速螢幕局部截圖。
    """
    def __init__(self):
        self.sct = mss.mss()

    def capture_region(self, x: int, y: int, w: int, h: int) -> Optional[np.ndarray]:
        """
        擷取螢幕上指定矩形區域 (x, y, w, h)，返回 numpy array 物件 (BGR 格式)。
        """
        try:
            # mss 接受的區域字典
            monitor = {
                "top": int(y),
                "left": int(x),
                "width": int(w),
                "height": int(h)
            }
            sct_img = self.sct.grab(monitor)
            
            # 從 mss (BGRA) 轉為 numpy array (BGR)，省略 PIL 中轉，大幅提升效能
            img_bgra = np.array(sct_img)
            img_bgr = img_bgra[:, :, :3]
            return img_bgr
        except Exception as e:
            print(f"螢幕擷取失敗: {e}")
            return None

    def close(self) -> None:
        """
        關閉 mss 資源。
        """
        if hasattr(self, 'sct') and self.sct:
            try:
                self.sct.close()
            except Exception:
                pass
