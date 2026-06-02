from core.controller import BotController

def test_is_detection_safe_thresholds():
    # 創建一個測試用的 BotController 實例
    # 注意：BotController 初始化會啟動兩個背景執行緒 (worker_thread, monitor_thread)
    # 我們在測試完後需要調用 stop() 以優雅地關閉，避免執行緒殘留
    config = {
        "min_confidence": 0.45,
        "max_low_confidence_cells": 9,
    }
    controller = BotController(config)
    
    try:
        obstacle_grid = [[0] * 6 for _ in range(5)]
        
        # 測試案例 1：沒有低信心度符石 (信心度皆為 1.0)
        confidence_grid_safe = [[1.0] * 6 for _ in range(5)]
        assert controller._is_detection_safe(confidence_grid_safe, obstacle_grid) is True

        # 測試案例 2：剛好有 9 顆低信心度符石 (應該仍然安全，可轉珠)
        confidence_grid_9_low = [[1.0] * 6 for _ in range(5)]
        # 將其中 9 顆設為 0.3 (低於 0.45)
        for i in range(9):
            r, c = divmod(i, 6)
            confidence_grid_9_low[r][c] = 0.3
        assert controller._is_detection_safe(confidence_grid_9_low, obstacle_grid) is True

        # 測試案例 3：有 10 顆低信心度符石 (應該判定為不安全，跳過不轉)
        confidence_grid_10_low = [[1.0] * 6 for _ in range(5)]
        # 將其中 10 顆設為 0.3
        for i in range(10):
            r, c = divmod(i, 6)
            confidence_grid_10_low[r][c] = 0.3
        assert controller._is_detection_safe(confidence_grid_10_low, obstacle_grid) is False
        
    finally:
        controller.stop()
