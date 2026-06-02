# TOSSolver

神魔之塔 6x5 轉珠助手。專案包含棋盤截圖、符石辨識、路徑求解、透明 overlay 與 Windows SendInput 自動拖曳。

## Windows 快速啟動 (推薦)

本專案已內建一鍵式啟動與環境建置工具。下載後僅需：

1. **右鍵點擊 [launch.bat](launch.bat) 選擇「以系統管理員身分執行」**。
2. 啟動器會自動搜尋您電腦中的 Python 環境、補全所有缺失的依賴庫（包含核心求解加速庫 `numba` 等），並在幾秒內直接開啟轉珠助手主介面。

*※ 註：由於全域熱鍵註冊與滑鼠拖曳需要與高權限模擬器互動，請務必使用「以系統管理員身分執行」啟動。*

## 手動安裝與執行 (開發者選項)

若您偏好手動安裝，請確保系統具備 Python 3.8+ 環境後執行：

```powershell
# 安裝所有必要依赖 (若有權限限制可加上 --user)
pip install -r requirements.txt

# 啟動主程式
python main.py
```

快捷鍵：

- `F1`: 擷取、辨識並求解
- `F2`: 清除 overlay
- `F3`: 手動辨識預覽
- `F4`: 辨識、求解並自動轉珠
- `F5`: 停止自動轉珠

## 求解模式

`config.json` 的 `solve_mode` 支援：

- `short_8c`: 找到 8 combo 以上的最短路徑就停止
- `max_combo`: 在步數限制內追求 combo 數
- `full_board`: 偏好高 combo 與高消除顆數
- `priority_color`: 目前等同 `full_board`，保留給指定屬性優先策略

## 安全設定

- `min_confidence`: 單格辨識信心下限，低於此值會被 GUI 標示
- `max_low_confidence_cells`: 自動起手允許的低信心格數
- `allow_obstacles`: 保留相容用；目前疑似障礙只會標示，不會阻止自動起手，也不會影響求解路徑

## 測試

```powershell
python -m pytest
```
