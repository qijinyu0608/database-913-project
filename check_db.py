from db_config import SessionLocal, engine
from models import *
from sqlalchemy import text, inspect


def check_connection():
    db = SessionLocal()
    try:
        print("------ 1. 测试数据库连接 ------")
        result = db.execute(text("SELECT 1")).scalar()
        print(f"✅ 数据库连接成功！(返回值为: {result})")

        print("\n------ 2. 检查数据库表结构 ------")
        inspector = inspect(engine)
        tables = inspector.get_table_names(schema='dbo')
        print(f"数据库中存在的表: {tables}")

        required_tables = ['tb_area_info', 'tb_monitor_record', 'tb_environment_data']
        for table in required_tables:
            if table not in tables:
                print(f"⚠️ 缺少必要表: {table} - 请运行 init_db.py 创建表结构")

        print("\n------ 3. 检查各表数据量 ------")
        tables = [
            ('区域信息 (AreaInfo)', AreaInfo),
            ('工作人员 (StaffInfo)', StaffInfo),
            ('监测设备 (MonitorDevice)', MonitorDevice),
            ('物种信息 (SpeciesInfo)', SpeciesInfo),
            ('环境数据 (EnvironmentData)', EnvironmentData),
            ('非法行为 (IllegalBehavior)', IllegalBehavior),
            ('科研项目 (ResearchProject)', ResearchProject),
        ]

        has_data = False
        for name, model in tables:
            count = db.query(model).count()
            print(f"📋 {name}: {count} 条数据")
            if count > 0:
                has_data = True

        print("\n------ 4. 检查模型与表映射 ------")
        try:
            # 测试查询一条环境数据
            env_data = db.query(EnvironmentData).first()
            if env_data:
                print(f"✅ 模型映射正常，示例数据: {env_data.data_id} - {env_data.monitor_value}")
        except Exception as e:
            print(f"⚠️ 模型映射可能存在问题: {e}")

        print("\n------ 5. 诊断结果 ------")
        if has_data:
            print("✅ 成功检测到数据！Web 界面应该能显示。")
            print("如果 Web 界面仍不显示，请检查模板文件中的变量名是否正确。")
        else:
            print("❌ 所有表的数据量均为 0！")
            print("请运行 init_db.py 初始化测试数据：python init_db.py")

    except Exception as e:
        print(f"❌ 发生错误: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    check_connection()