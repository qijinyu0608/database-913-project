from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import urllib

# 配置数据库连接信息 (请修改为你的实际配置)
# 使用 pyodbc 连接 SQL Server
params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=123.57.238.87;"  # 或你的服务器IP
    "DATABASE=national_park_db;"
    "UID=sa;"            # 建议使用系统管理员权限运行持久层代码，实际业务中可切换不同用户
    "PWD=123456;"
)

# 创建引擎
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}", echo=False)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()

# 获取数据库会话工具函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()