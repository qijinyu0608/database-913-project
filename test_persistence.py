import unittest
import datetime
# 忽略 SQLAlchemy 的版本警告
import warnings
from sqlalchemy import exc, MetaData

warnings.simplefilter("ignore", category=exc.SAWarning)

from db_config import SessionLocal, engine, Base
from models import *
from dao import BioDiversityDAO, EnvironmentDAO, VisitorDAO, EnforcementDAO, ResearchDAO


class TestCRUD(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """1. 重置数据库结构 (删表重建)"""
        print("\n=== 初始化测试数据库环境 ===")
        metadata = MetaData()
        metadata.reflect(bind=engine)
        metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        self.db = SessionLocal()
        self.init_foundation_data()

    def tearDown(self):
        self.db.close()

    def init_foundation_data(self):
        """准备基础数据 (区域、设备、员工、物种)"""
        # 注意：这里的最大容量设置为 1000
        if not self.db.get(AreaInfo, "AREA-001"):
            self.db.add(AreaInfo(area_id="AREA-001", area_name="核心区", area_level="一级", area_lng_range="0",
                                 area_lat_range="0"))
            self.db.add(FlowControl(area_id="AREA-001", daily_max_capacity=1000, real_time_visitor_count=0,
                                    warning_threshold=800, current_status="正常"))
            self.db.add(StaffInfo(staff_id="STAFF-001", staff_name="张三", staff_role="监测员", department="监测部",
                                  contact_phone="123"))
            self.db.add(MonitorDevice(device_id="DEV-001", device_type="相机", deploy_area_id="AREA-001",
                                      install_time=datetime.date.today(), calibration_cycle=30, running_status="正常",
                                      communication_protocol="4G"))
            self.db.add(SpeciesInfo(species_id="SP-001", species_name_cn="大熊猫", species_name_latin="Ailuropoda",
                                    species_category="哺乳纲", protection_level="一级"))
            # 准备指标
            self.db.add(MonitorIndex(index_id="IDX-001", index_name="气温", unit="C", standard_upper=35,
                                     monitor_frequency="时"))
            # 准备执法设备与人员
            self.db.add(LawEnforceDevice(device_id="LD-001", device_type="记录仪", device_status="正常",
                                         last_check_time=datetime.date.today()))
            self.db.add(LawEnforcer(enforcer_id="LE-001", enforcer_name="王五", department="执法队",
                                    enforcement_permission="全", contact_phone="110", law_enforce_device_id="LD-001"))
            # 准备科研人员
            self.db.add(ResearcherInfo(researcher_id="RE-001", researcher_name="李教授", affiliated_unit="大学",
                                       research_field="生态", contact_info="mail"))
            self.db.commit()

    # --- 1. 生物多样性 CRUD 测试 ---
    def test_01_biodiversity_crud(self):
        print("\n[测试] 1. 生物多样性业务 CRUD")
        dao = BioDiversityDAO(self.db)
        rec_id = "MR-TEST-001"

        # 1. Create
        data = {
            "record_id": rec_id, "species_id": "SP-001", "device_id": "DEV-001",
            "monitor_time": datetime.datetime.now(), "monitor_lng": 103.0, "monitor_lat": 30.0,
            "monitor_method": "红外", "monitor_content": "发现踪迹", "recorder_id": "STAFF-001", "data_status": "待审"
        }
        dao.add_monitor_record(data)
        print(f"  > 新增成功: {rec_id}")

        # 2. Read
        rec = dao.get_record_by_id(rec_id)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.monitor_content, "发现踪迹")
        print(f"  > 查询成功: {rec.monitor_content}")

        # 3. Update
        updated = dao.update_record_content(rec_id, "发现踪迹-已确认", "已归档")
        self.assertEqual(updated.monitor_content, "发现踪迹-已确认")
        self.assertEqual(updated.data_status, "已归档")
        print(f"  > 修改成功: {updated.monitor_content}")

        # 4. Delete
        dao.delete_record(rec_id)
        deleted = dao.get_record_by_id(rec_id)
        self.assertIsNone(deleted)
        print("  > 删除成功")

    # --- 2. 生态环境 CRUD 测试 ---
    def test_02_environment_crud(self):
        print("\n[测试] 2. 生态环境业务 CRUD")
        dao = EnvironmentDAO(self.db)
        data_id = "ED-TEST-001"

        # 1. Create (触发超标逻辑)
        data = {
            "data_id": data_id, "index_id": "IDX-001", "device_id": "DEV-001",
            "collect_time": datetime.datetime.now(), "monitor_value": 40.0, "area_id": "AREA-001", "data_quality": "未知"
        }
        dao.add_environment_data(data)

        # 2. Read
        res = dao.get_data_by_id(data_id)
        self.assertEqual(res.data_quality, "差", "40度应判定为差")
        print(f"  > 新增并查询成功，质量判定: {res.data_quality}")

        # 3. Update (修正数值)
        dao.update_data_value(data_id, 30.0)  # 改为正常值
        res_updated = dao.get_data_by_id(data_id)
        self.assertEqual(res_updated.monitor_value, 30.0)
        self.assertEqual(res_updated.data_quality, "优", "30度应自动修正为优")
        print("  > 修改数值并自动修正质量成功")

        # 4. Delete
        dao.delete_data(data_id)
        self.assertIsNone(dao.get_data_by_id(data_id))
        print("  > 删除成功")

    # --- 3. 游客管理 CRUD 测试 ---
    def test_03_visitor_crud(self):
        print("\n[测试] 3. 游客管理业务 CRUD")
        dao = VisitorDAO(self.db)
        res_id = "RR-TEST-001"

        # 1. Create (预约)
        vis_data = {"visitor_id": "VI-001", "visitor_name": "游客A", "id_card": "510111199901010001",
                    "contact_phone": "139", "check_in_method": "网"}
        res_data = {"reservation_id": res_id, "reservation_date": datetime.date.today(), "check_in_period": "AM",
                    "companion_count": 0, "reservation_status": "有效", "ticket_amount": 100, "payment_status": "Paid"}
        dao.make_reservation(vis_data, res_data)
        print("  > 预约新增成功")

        # 2. Update (流量)
        # 【关键修改】 将 900 改为 1001，确保其大于 capacity (1000)，从而触发限流
        dao.update_flow_control("AREA-001", 1001)
        flow = self.db.get(FlowControl, "AREA-001")
        self.assertEqual(flow.current_status, "限流", "超过1000应触发限流")
        print("  > 流量更新及熔断触发成功")

        # 3. Update (取消预约)
        dao.cancel_reservation(res_id)
        r = dao.get_reservation(res_id)
        self.assertEqual(r.reservation_status, "已取消")
        print("  > 预约取消成功")

        # 4. Delete (物理删除)
        dao.delete_reservation_physically(res_id)
        self.assertIsNone(dao.get_reservation(res_id))
        print("  > 预约单物理删除成功")

    # --- 4. 执法监管 CRUD 测试 ---
    def test_04_enforcement_crud(self):
        print("\n[测试] 4. 执法监管业务 CRUD")
        dao = EnforcementDAO(self.db)
        beh_id = "IB-TEST-001"

        # 1. Create
        ill_data = {"behavior_id": beh_id, "behavior_type": "偷猎", "occur_time": datetime.datetime.now(),
                    "occur_area_id": "AREA-001", "evidence_path": "path", "handle_status": "新",
                    "enforcer_id": "LE-001", "penalty_basis": "法"}
        disp_data = {"dispatch_id": "DIS-001", "enforcer_id": "LE-001", "dispatch_time": datetime.datetime.now(),
                     "dispatch_status": "Go"}
        dao.create_dispatch(ill_data, disp_data)
        print("  > 案件与调度新增成功")

        # 2. Update (结案)
        dao.close_case(beh_id, "罚款500元")
        case = dao.get_behavior_detail(beh_id)
        self.assertEqual(case.handle_status, "已处理")
        self.assertEqual(case.handle_result, "罚款500元")
        print("  > 结案更新成功")

        # 3. Delete
        success = dao.delete_case_record(beh_id)
        self.assertTrue(success)
        self.assertIsNone(dao.get_behavior_detail(beh_id))
        print("  > 案件及关联调度删除成功")

    # --- 5. 科研支撑 CRUD 测试 ---
    def test_05_research_crud(self):
        print("\n[测试] 5. 科研支撑业务 CRUD")
        dao = ResearchDAO(self.db)
        proj_id = "RP-TEST-001"

        # 1. Create
        p_data = {
            "project_id": proj_id, "project_name": "测试项目", "leader_id": "RE-001",
            "application_unit": "School", "project_start_date": datetime.date.today(),
            "project_end_date": datetime.date.today(), "project_status": "在研", "research_field": "Eco"
        }
        dao.add_project(p_data)
        print("  > 项目立项成功")

        # 2. Read
        p = dao.get_project(proj_id)
        self.assertEqual(p.project_name, "测试项目")

        # 3. Update
        dao.update_project_status(proj_id, "结题")
        p2 = dao.get_project(proj_id)
        self.assertEqual(p2.project_status, "结题")
        print("  > 项目状态更新成功")

        # 4. Delete
        dao.delete_project(proj_id)
        self.assertIsNone(dao.get_project(proj_id))
        print("  > 项目删除成功")


if __name__ == '__main__':
    unittest.main()