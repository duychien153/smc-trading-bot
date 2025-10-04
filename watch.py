#!/usr/bin/env python3
"""
File watcher để tự động chạy lại main.py khi có thay đổi
"""

import os
import sys
import subprocess
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PythonFileHandler(FileSystemEventHandler):
    def __init__(self, file_to_watch, python_path):
        self.file_to_watch = file_to_watch
        self.python_path = python_path
        self.last_run = 0
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Chỉ theo dõi file main.py
        if event.src_path.endswith('main.py'):
            current_time = time.time()
            # Tránh chạy quá nhiều lần (debounce 1 giây)
            if current_time - self.last_run > 1:
                self.last_run = current_time
                print(f"\n🔄 Phát hiện thay đổi: {event.src_path}")
                print("=" * 50)
                self.run_script()
                print("=" * 50)
    
    def run_script(self):
        try:
            # Chạy main.py với Python path từ venv
            result = subprocess.run(
                [self.python_path, self.file_to_watch], 
                capture_output=True, 
                text=True,
                cwd=os.path.dirname(self.file_to_watch)
            )
            
            # In output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
                
            if result.returncode == 0:
                print("✅ Script chạy thành công")
            else:
                print(f"❌ Script lỗi với exit code: {result.returncode}")
                
        except Exception as e:
            print(f"❌ Lỗi khi chạy script: {e}")

def main():
    # Đường dẫn file cần theo dõi
    file_to_watch = "/Users/chiennd/bot-trade/main.py"
    python_path = "/Users/chiennd/bot-trade/venv/bin/python"
    watch_directory = "/Users/chiennd/bot-trade"
    
    if not os.path.exists(file_to_watch):
        print(f"❌ Không tìm thấy file: {file_to_watch}")
        sys.exit(1)
    
    print(f"👀 Đang theo dõi file: {file_to_watch}")
    print("💡 Mỗi khi bạn lưu file, script sẽ tự động chạy lại")
    print("🛑 Nhấn Ctrl+C để dừng")
    print("=" * 50)
    
    # Chạy script một lần đầu tiên
    handler = PythonFileHandler(file_to_watch, python_path)
    handler.run_script()
    
    # Bắt đầu theo dõi
    observer = Observer()
    observer.schedule(handler, watch_directory, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Đã dừng file watcher")
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()