import pyodbc
from datetime import datetime
import os


class BackupManager:
    """数据库备份与恢复管理器"""

    DB_NAME = "national_park_db"

    # 备份路径 (请确保该文件夹已存在且有权限)
    BACKUP_DIR = r"C:\DB_Backups"

    def __init__(self):
        # 数据库连接配置 (请确保 SERVER 和 PWD 正确)
        self.conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=123.57.238.87;"
            "DATABASE=master;"
            "UID=sa;PWD=123456;"
        )

    def _ensure_dir_exists(self):
        """辅助方法：尝试创建目录（仅对本地有效）"""
        if not os.path.exists(self.BACKUP_DIR):
            try:
                os.makedirs(self.BACKUP_DIR)
                print(f"已尝试自动创建备份目录: {self.BACKUP_DIR}")
            except Exception as e:
                print(f"警告: 无法创建目录 (若是远程备份请忽略): {e}")

    def full_backup(self):
        """每周全量备份"""
        self._ensure_dir_exists()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        file_path = os.path.join(self.BACKUP_DIR, f"{self.DB_NAME}_FULL_{timestamp}.bak")

        sql = f"BACKUP DATABASE [{self.DB_NAME}] TO DISK = '{file_path}' WITH INIT, NAME = 'Full Backup'"

        try:
            with pyodbc.connect(self.conn_str, autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                print(f"[成功] 全量备份已完成: {file_path}")
        except Exception as e:
            print(f"[失败] 全量备份失败: {e}")

    def differential_backup(self):
        """每日增量(差异)备份"""
        self._ensure_dir_exists()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        file_path = os.path.join(self.BACKUP_DIR, f"{self.DB_NAME}_DIFF_{timestamp}.bak")

        sql = f"BACKUP DATABASE [{self.DB_NAME}] TO DISK = '{file_path}' WITH DIFFERENTIAL, NAME = 'Diff Backup'"

        try:
            with pyodbc.connect(self.conn_str, autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                print(f"[成功] 增量备份已完成: {file_path}")
        except Exception as e:
            print(f"[失败] 增量备份失败: {e}")


# 持久层设计/backup_strategy.py 底部

# if __name__ == "__main__":
#     manager = BackupManager()
#
#     print("--- 正在执行初始化全量备份（修复报错） ---")
#     manager.full_backup()  # <--- 强制调用全量备份
#
#     print("\n--- 全量备份完成后，测试增量备份 ---")
#     manager.differential_backup()

# --- 日常运行入口 ---
if __name__ == "__main__":
    manager = BackupManager()

    # 获取今天是星期几 (0=周一, 6=周日)
    today = datetime.now().weekday()

    print(f"当前时间: {datetime.now()}")

    # 策略：周日做全量，周一到周六做增量
    if today == 6:
        print(">>今天是周日，执行【全量备份】...")
        manager.full_backup()
    else:
        print(f">>今天是周{today + 1}，执行【增量备份】...")
        manager.differential_backup()