import threading
import time
import queue
from typing import Dict, Any, Optional, List, Callable, Tuple

from core.capturer import ScreenCapturer
from core.detector import OrbDetector
from core.solver import TOSSolver
from core.auto_player import AutoPlayer, get_mouse_pos

class BotController:
    """
    任務調度控制器。負責統籌截圖、辨識、求解與自動轉珠。
    使用單一背景工作執行緒處理所有耗時任務，確保主執行緒（GUI）不卡頓。
    包含鎖定機制保護共用變數讀寫。
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.capturer = ScreenCapturer()
        self.detector = OrbDetector()
        
        self.auto_player = AutoPlayer(
            move_delay_ms=self.config.get("move_delay_ms", 45),
            start_delay_ms=self.config.get("start_delay_ms", 300),
            human_move_threshold=self.config.get("mouse_move_threshold", 30)
        )
        
        self.last_scan_grid: Optional[List[List[int]]] = None
        self.last_played_grid: Optional[List[List[int]]] = None
        self.grid_lock = threading.Lock()
        
        # 回呼函式 (用於安全地將狀態同步到 GUI)
        self.on_board_detected: Optional[Callable[[List[List[int]], List[List[int]], List[List[float]]], None]] = None
        self.on_path_solved: Optional[Callable[[List[Tuple[int, int]]], None]] = None
        self.on_auto_trigger_disabled: Optional[Callable[[], None]] = None
        self.on_clear_path: Optional[Callable[[], None]] = None
        
        # 任務佇列與執行緒
        self.task_queue = queue.Queue()
        self.is_running = True
        
        # 工作執行緒：專職處理手動觸發的辨識/求解/轉珠
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        # 自動起手監控執行緒：專職背景監控盤面穩定度
        self.monitor_thread = threading.Thread(target=self._auto_monitor_loop, daemon=True)
        self.monitor_thread.start()

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新內部設定與各元件組態"""
        self.config.update(new_config)
        self.auto_player.move_delay_ms = self.config.get("move_delay_ms", 45)
        self.auto_player.start_delay_ms = self.config.get("start_delay_ms", 300)
        self.auto_player.human_move_threshold = self.config.get("mouse_move_threshold", 30)
        
    def enqueue_task(self, task_type: str) -> None:
        """將手動任務放入佇列"""
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except queue.Empty:
                break
        self.task_queue.put(task_type)

    def stop(self) -> None:
        """優雅關閉控制器"""
        self.is_running = False
        self.auto_player.stop()
        self.capturer.close()

    def _worker_loop(self) -> None:
        while self.is_running:
            try:
                task = self.task_queue.get(timeout=0.1)
                if task == 'detect':
                    self._process_detect()
                elif task == 'solve':
                    self._process_solve()
                elif task == 'auto_play':
                    self._process_auto_play()
                self.task_queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                print(f"工作執行緒發生未預期錯誤: {e}")

    def _capture_and_detect(self) -> Optional[Tuple[List[List[int]], List[List[int]], List[List[float]]]]:
        """擷取並辨識螢幕"""
        x = self.config.get("crop_x", 0)
        y = self.config.get("crop_y", 0)
        w = self.config.get("crop_w", 0)
        h = self.config.get("crop_h", 0)
        
        img = self.capturer.capture_region(x, y, w, h)
        if img is None:
            return None
            
        board_grid, obstacle_grid, confidence_grid = self.detector.detect_board(img)
        if self.on_board_detected:
            self.on_board_detected(board_grid, obstacle_grid, confidence_grid)
        return board_grid, obstacle_grid, confidence_grid

    def _is_detection_safe(self, confidence_grid: List[List[float]], obstacle_grid: List[List[int]]) -> bool:
        min_conf = self.config.get("min_confidence", 0.45)
        max_low_cells = self.config.get("max_low_confidence_cells", 2)
        
        low_conf_count = 0
        for row in confidence_grid:
            for conf in row:
                if conf < min_conf:
                    low_conf_count += 1
        
        if low_conf_count > max_low_cells:
            print(f"辨識信心不足 (低於{min_conf}的數量: {low_conf_count})，跳過此盤面。")
            return False
            
        return True

    def _process_detect(self) -> None:
        res = self._capture_and_detect()
        if res:
            grid, obs, _confidence = res
            try:
                print("--- 棋盤手動擷取辨識預覽結果 ---")
                print(self.detector.print_board_text(grid))
            except Exception:
                pass

    def _process_solve(self) -> None:
        res = self._capture_and_detect()
        if not res:
            print("擷取螢幕失敗，請確認校準座標是否正確！")
            return
            
        grid, obs, _confidence = res
        max_steps = self.config.get("max_steps", 30)
        beam_width = self.config.get("beam_width", 100)
        solve_mode = self.config.get("solve_mode", "max_combo")
        target_combo = self.config.get("target_combo", 8)
        
        solver = TOSSolver(max_steps=max_steps, beam_width=beam_width)
        t0 = time.time()
        best_path, est_combos, est_cleared = solver.solve(
            grid, None, solve_mode=solve_mode, target_combo=target_combo
        )
        t1 = time.time()
        print(f"路徑計算完成，耗時: {(t1 - t0) * 1000:.2f} 毫秒")
        
        if self.on_path_solved:
            self.on_path_solved(best_path)

    def _process_auto_play(self) -> None:
        res = self._capture_and_detect()
        if not res:
            print("擷取螢幕失敗，請確認校準座標是否正確！")
            return
            
        grid, obs, confidence = res
        if not self._is_detection_safe(confidence, obs):
            return

        time.sleep(0.15)
        confirm_res = self._capture_and_detect()
        if not confirm_res:
            return
        confirm_grid, confirm_obs, confirm_confidence = confirm_res
        if confirm_grid != grid:
            print("二次確認時盤面已變動，取消自動起手。")
            return
        if not self._is_detection_safe(confirm_confidence, confirm_obs):
            return
        with self.grid_lock:
            self.last_played_grid = grid
        
        max_steps = self.config.get("max_steps", 30)
        beam_width = self.config.get("beam_width", 100)
        solve_mode = self.config.get("solve_mode", "max_combo")
        target_combo = self.config.get("target_combo", 8)
        
        solver = TOSSolver(max_steps=max_steps, beam_width=beam_width)
        t0 = time.time()
        best_path, est_combos, est_cleared = solver.solve(
            grid, None, solve_mode=solve_mode, target_combo=target_combo
        )
        t1 = time.time()
        print(f"路徑計算完成，耗時: {(t1 - t0) * 1000:.2f} 毫秒")
        
        if self.on_path_solved:
            self.on_path_solved(best_path)
            
        time.sleep(0.5)
        print(f"開始自動轉珠！預估 {est_combos} Combos, {len(best_path)-1} 步...")
        
        x = self.config.get("crop_x", 0)
        y = self.config.get("crop_y", 0)
        w = self.config.get("crop_w", 0)
        h = self.config.get("crop_h", 0)
        
        success = self.auto_player.play(best_path, x, y, w, h)
        if success is False and self.on_auto_trigger_disabled:
            self.on_auto_trigger_disabled()
            
        time.sleep(0.3)
        if self.on_clear_path:
            self.on_clear_path()

    def _auto_monitor_loop(self) -> None:
        """獨立執行緒，定期檢測畫面是否穩定且適合起手。"""
        while self.is_running:
            interval_ms = int(float(self.config.get("auto_interval_s", 1.0)) * 1000)
            interval_s = max(0.1, interval_ms / 1000.0)
            
            time.sleep(interval_s)
            
            # 若未開啟自動起手，或正在轉珠，則不進行監控
            if self.config.get("auto_trigger", 0) == 0 or self.auto_player.is_running:
                continue
                
            # 若工作佇列中已有排隊的任務，暫停監控避免搶資源
            if not self.task_queue.empty():
                continue
                
            try:
                start_mouse_x, start_mouse_y = get_mouse_pos()
            except Exception:
                start_mouse_x, start_mouse_y = None, None
                
            mouse_thresh = int(self.config.get("mouse_move_threshold", 30))
            
            res = self._capture_and_detect()
            if not res:
                continue
                
            grid, obs, confidence = res
                
            # 檢驗盤面是否有足夠多的有效符石 (30顆)
            valid_orbs_count = sum(sum(1 for orb in row if 0 <= orb <= 5) for row in grid)
            if valid_orbs_count < 30:
                continue
            if not self._is_detection_safe(confidence, obs):
                continue
                
            with self.grid_lock:
                if self.last_scan_grid is None:
                    self.last_scan_grid = grid
                    continue
                    
                is_stable = (grid == self.last_scan_grid)
                self.last_scan_grid = grid
                
                last_played = self.last_played_grid
            
            if is_stable and grid != last_played:
                moved = False
                try:
                    if start_mouse_x is not None:
                        cur_x, cur_y = get_mouse_pos()
                        if abs(cur_x - start_mouse_x) > mouse_thresh or abs(cur_y - start_mouse_y) > mouse_thresh:
                            moved = True
                except Exception:
                    moved = False
                    
                if moved:
                    print("偵測到使用者移動滑鼠，取消自動起手。")
                    if self.on_auto_trigger_disabled:
                        self.on_auto_trigger_disabled()
                    continue
                    
                print("偵測到穩定的新棋盤配置！觸發自動轉珠...")
                with self.grid_lock:
                    self.last_played_grid = grid
                self.enqueue_task('auto_play')
