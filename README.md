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

## 求解模式與自選 Combo 功能

專案內建強大的多重轉珠演算法，支援靈活的消珠策略與自選 Combo 功能，可在 GUI 面板「轉珠策略」下拉選單中直接切換（或透過 `config.json` 的 `solve_mode` 進行設定）：

- **最大 Combo (`max_combo`)**：在路徑步數限制內，全力追求最高的 Combo 數。
- **首消全版 (`full_board`)**：在追求高 Combo 的同時，優先偏好消除最多顆數的符石，以達到清版與最高爆發效果。
- **至少指定 Combo (`at_least_c`)**：使用者自選目標 Combo 數（支援 **1~10 Combo**）。當演算法搜尋到滿足 $\ge N$ Combo 的最短路徑時將立即停止，極大化轉珠速度與路徑精簡度，最適合用來破解特定 Combo 盾。
- **剛好指定 Combo (`exactly_c`)**：使用者自選目標 Combo 數（支援 **1~10 Combo**）。演算法會精準調整消除版面，確保最終消珠結果剛好等於 $N$ Combo，是破解「剛好 N Combo 盾」的終極利器。
- `short_8c`：歷史相容模式，找到 8 Combo 以上的最短路徑即停。
- `priority_color`：目前等同 `full_board`。

> [!TIP]
> 轉珠助手 GUI 具備流暢的控制連動。當您在「轉珠策略」選單中選擇 **「至少指定 Combo」** 或 **「剛好指定 Combo」** 時，「目標 Combo 數」選擇框會自動亮起並啟用；若選擇其他策略，該欄位則會智慧型自動變灰並停用，避免操作混淆。

## 演算法與核心參數說明

除了在 GUI 直觀操作外，您也可以在專案的 `config.json` 中配置或查看以下核心參數：

- `solve_mode`：轉珠策略（支援上述策略鍵值）。
- `target_combo`：目標 Combo 數（支援整數 `1` ~ `10`，預設為 `8`）。
- `max_steps`：最大轉珠路徑步數（支援 `10` ~ `200` 步）。
- `beam_width`：束搜尋（Beam Search）寬度，數值越大路徑質量越高但運算稍慢（支援 `10` ~ `2000`）。
- `move_delay_ms`：滑鼠拖曳轉珠時每一步的移動速度（ms），速度越小轉越快。
- `start_delay_ms`：起手前的延遲時間（ms）。
- `min_confidence`：單格辨識信心下限，低於此值會被 GUI 標示。
- `max_low_confidence_cells`：自動起手允許的低信心格數。
- `allow_obstacles`：保留相容用；目前疑似障礙只會標示，不會阻止自動起手，也不會影響求解路徑。

## 測試

```powershell
python -m pytest
```
