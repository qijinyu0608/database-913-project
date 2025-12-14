import pyodbc

# 请确保这里的信息与您 db_config.py 里的一致
SERVER = '123.57.238.87'      # 如果是本机，用 localhost
DATABASE = 'national_park_db'
USERNAME = 'sa'
PASSWORD = '123456'       # 您的真实密码

try:
    print(f"正在尝试连接 {SERVER}...")
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'
    conn = pyodbc.connect(conn_str, timeout=5)
    print("✅ 连接成功！数据库配置已修复。")
    conn.close()
except Exception as e:
    print("❌ 连接失败。错误详情：")
    print(e)