# 文件名: init_db.py
from db_config import SessionLocal, engine, Base
from models import *
import datetime


def init_data():
    # 1. 创建表结构 (如果不存在)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("正在初始化基础数据...")

        # --- 区域 ---
        if not db.get(AreaInfo, "AREA-001"):
            db.add(AreaInfo(area_id="AREA-001", area_name="核心保护区", area_level="一级", area_lng_range="103.1",
                            area_lat_range="30.1"))
            db.add(FlowControl(area_id="AREA-001", daily_max_capacity=1000, real_time_visitor_count=500,
                               warning_threshold=800, current_status="正常"))

        # --- 员工 ---
        if not db.get(StaffInfo, "STAFF-001"):
            db.add(StaffInfo(staff_id="STAFF-001", staff_name="张三", staff_role="监测员", department="监测部",
                             contact_phone="13800000001"))
            # 执法员
            db.add(LawEnforceDevice(device_id="LD-001", device_type="执法记录仪", device_status="正常",
                                    last_check_time=datetime.date.today()))
            db.add(LawEnforcer(enforcer_id="LE-001", enforcer_name="李四", department="综合执法队",
                               enforcement_permission="全区", contact_phone="110", law_enforce_device_id="LD-001"))

        # --- 设备 ---
        if not db.get(MonitorDevice, "DEV-001"):
            db.add(MonitorDevice(device_id="DEV-001", device_type="红外相机", deploy_area_id="AREA-001",
                                 install_time=datetime.date.today(), calibration_cycle=30, running_status="正常",
                                 communication_protocol="4G"))

        # --- 物种 ---
        if not db.get(SpeciesInfo, "SP-001"):
            db.add(SpeciesInfo(species_id="SP-001", species_name_cn="大熊猫", species_name_latin="Ailuropoda",
                               species_category="哺乳纲", protection_level="一级"))

        # --- 环境指标 ---
        if not db.get(MonitorIndex, "IDX-001"):
            db.add(MonitorIndex(index_id="IDX-001", index_name="空气温度", unit="℃", standard_upper=35.0,
                                monitor_frequency="1小时"))
            # 添加一条环境数据用于展示
            db.add(EnvironmentData(data_id="ED-INIT-01", index_id="IDX-001", device_id="DEV-001",
                                   collect_time=datetime.datetime.now(), monitor_value=25.5, area_id="AREA-001",
                                   data_quality="优"))

        # --- 科研 ---
        if not db.get(ResearcherInfo, "RE-001"):
            db.add(ResearcherInfo(researcher_id="RE-001", researcher_name="王教授", affiliated_unit="林业大学",
                                  research_field="生态学", contact_info="wang@univ.edu"))
            db.add(ResearchProject(project_id="RP-001", project_name="秦岭生态修复研究", leader_id="RE-001",
                                   application_unit="林业大学", project_start_date=datetime.date.today(),
                                   project_end_date=datetime.date.today(), project_status="在研",
                                   research_field="生态修复"))

        db.commit()
        print("✅ 数据初始化完成！现在启动 app.py 应该能看到数据了。")
    except Exception as e:
        db.rollback()
        print(f"❌ 初始化失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    init_data()