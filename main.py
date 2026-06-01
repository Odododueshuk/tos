import os
import sys
import ctypes
import keyboard
from gui.main_window import MainWindow
from core.controller import BotController

def main():
    # 宣告 Windows DPI 感知，避免 UI 和滑鼠控制受系統縮放影響
    if sys.platform.startswith("win"):
        try:
            # 優先嘗試 Windows 8.1+ 的 per-monitor DPI 感知
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                # 退回到 Windows Vista+ 的系統級 DPI 感知
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
                
    # 解決 Windows 終端印出 Emoji 引起的 Unicode 編碼問題
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # 確保工作目錄在目前檔案所在的目錄，以便順利讀取 config.json 等資源
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    config_path = "config.json"
    
    # 創建主視窗與控制器
    print("正在啟動神魔之塔轉珠助手 GUI 面板...")
    controller = BotController({})
    app = MainWindow(config_path, controller)
    
    # 綁定全域快捷鍵
    # keyboard 庫會在獨立的背景執行緒中觸發回呼
    # 我們已在 MainWindow 中使用 root.after 確保所有 GUI 更新都回到 Tkinter 主執行緒執行，100% 安全執行！
    try:
        keyboard.add_hotkey("F1", lambda: app.root.after(0, app.trigger_solve))
        keyboard.add_hotkey("F2", lambda: app.root.after(0, app.trigger_clear))
        keyboard.add_hotkey("F3", lambda: app.root.after(0, app.trigger_detection))
        keyboard.add_hotkey("F4", lambda: app.root.after(0, app.trigger_auto_play))
        keyboard.add_hotkey("F5", lambda: app.root.after(0, app.trigger_stop_auto))
        print("全域熱鍵註冊成功：")
        print("  - [F1] 擷取、辨識並在模擬器畫面上繪製最佳路徑")
        print("  - [F2] 清除置頂透明路徑")
        print("  - [F3] 手動擷取並更新控制面板的 6x5 符石預覽")
        print("  - [F4] 全自動轉珠（辨識 → 求解 → 自動拖曳滑鼠轉珠）")
        print("  - [F5] 緊急停止自動轉珠")
    except Exception as e:
        print(f"註冊全域熱鍵失敗 (請確認是否具備系統管理員權限): {e}")
        
    # 設定視窗關閉時的清理回呼，釋放全域熱鍵與擷取資源，避免背景殘留
    def on_closing():
        print("正在關閉轉珠助手，釋放資源...")
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        app.cleanup()
        app.root.destroy()
        sys.exit(0)
        
    app.root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 啟動應用程式
    app.run()

if __name__ == "__main__":
    main()
