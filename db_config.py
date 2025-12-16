import os
import urllib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# 原有普通用户配置
SERVER = os.getenv("DB_SERVER", "localhost")
DATABASE = os.getenv("DB_NAME", "national_park_db")
USERNAME = os.getenv("DB_USER", "sa")
PASSWORD = os.getenv("DB_PASSWORD")

if not PASSWORD:
    raise ValueError("错误：未找到数据库密码，请检查 .env.html 文件配置！")

# 新增 root 高权限用户配置
ROOT_USERNAME = os.getenv("ROOT_DB_USER", "root")
ROOT_PASSWORD = os.getenv("ROOT_DB_PASSWORD", "root")

# 普通用户连接字符串
connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"UID={USERNAME};"
    f"PWD={PASSWORD};"
)

# root 用户连接字符串（高权限）
root_connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"UID={ROOT_USERNAME};"
    f"PWD={ROOT_PASSWORD};"
)

# 编码连接字符串
params = urllib.parse.quote_plus(connection_string)
root_params = urllib.parse.quote_plus(root_connection_string)

# 普通用户引擎
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", echo=False)

# root 用户引擎（高权限）
root_engine = create_engine(f"mssql+pyodbc:///?odbc_connect={root_params}", echo=False)

# 普通会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# root 会话工厂（高权限）
RootSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=root_engine)

Base = declarative_base()

# 普通数据库会话工具函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# root 高权限数据库会话工具函数
def get_root_db():
    """高权限数据库会话（用于 root 用户直接访问数据库）"""
    db = RootSessionLocal()
    try:
        yield db
    finally:
        db.close()