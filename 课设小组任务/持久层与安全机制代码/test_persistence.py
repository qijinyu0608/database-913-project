import unittest
import datetime
from db_config import SessionLocal, engine, Base
from models import *
from dao import BioDiversityDAO, EnvironmentDAO, VisitorDAO, EnforcementDAO, ResearchDAO


class TestNationalParkSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """所有测试开始前，重置数据库结构"""
        # 1. 这一步是关键：创建一个空的 MetaData，绑定引擎
        from sqlalchemy import MetaData
        metadata = MetaData()

        # 2. 让 SQLAlchemy 去数据库里“读取”所有已经存在的表结构
        # 这样即使 models.py 里漏写的表，也能被读出来
        metadata.reflect(bind=engine)

        # 3. 删除数据库里读取到的所有表 (这样就能自动处理外键依赖顺序了)
        metadata.drop_all(bind=engine)

        # 4. 重新按照我们现在的代码创建表
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        self.db = SessionLocal()
        # 准备基础数据：区域、员工、设备
        self.init_foundation_data()

    def tearDown(self):
        self.db.close()

    def init_foundation_data(self):
        """初始化共享基础数据"""
        if not self.db.get(AreaInfo, "AREA-001"):
            area = AreaInfo(area_id="AREA-001", area_name="核心区", area_level="核心保护区",
                            area_lng_range="103.1-103.2", area_lat_range="30.1-30.2")
            self.db.add(area)
            # 初始化流量控制
            flow = FlowControl(area_id="AREA-001", daily_max_capacity=1000,
                               real_time_visitor_count=0, warning_threshold=800, current_status="正常")
            self.db.add(flow)

        if not self.db.get(StaffInfo, "STAFF-001"):
            staff = StaffInfo(staff_id="STAFF-001", staff_name="张三", staff_role="生态监测员",
                              department="监测部", contact_phone="13800000000")
            self.db.add(staff)

        if not self.db.get(MonitorDevice, "DEV-001"):
            dev = MonitorDevice(device_id="DEV-001", device_type="传感器", deploy_area_id="AREA-001",
                                install_time=datetime.date.today(), calibration_cycle=30,
                                running_status="正常", communication_protocol="4G")
            self.db.add(dev)

        self.db.commit()

    # --- 1. 生物多样性测试 ---
    def test_biodiversity_flow(self):
        dao = BioDiversityDAO(self.db)
        # 准备物种
        species = SpeciesInfo(species_id="SP-001", species_name_cn="大熊猫", species_name_latin="Ailuropoda",
                              species_category="哺乳纲", protection_level="一级")
        self.db.add(species)
        self.db.commit()

        # 增加监测记录
        data = {
            "record_id": "MR-TEST-001", "species_id": "SP-001", "device_id": "DEV-001",
            "monitor_time": datetime.datetime.now(), "monitor_lng": 103.1, "monitor_lat": 30.1,
            "monitor_method": "红外相机", "monitor_content": "path/to/img",
            "recorder_id": "STAFF-001", "data_status": "待核实"
        }
        rec = dao.add_monitor_record(data)
        self.assertIsNotNone(rec)
        print(">> 生物多样性业务：监测记录添加成功")

    # --- 2. 生态环境测试 ---
    def test_environment_flow(self):
        dao = EnvironmentDAO(self.db)
        # 准备指标
        idx = MonitorIndex(index_id="IDX-001", index_name="温度", unit="C",
                           standard_upper=40, monitor_frequency="时")
        self.db.add(idx)
        self.db.commit()

        # 添加超标数据，验证逻辑
        data = {
            "data_id": "ED-TEST-001", "index_id": "IDX-001", "device_id": "DEV-001",
            "collect_time": datetime.datetime.now(), "monitor_value": 45.0,  # 超标
            "area_id": "AREA-001", "data_quality": "待定"
        }
        res = dao.add_environment_data(data)
        self.assertEqual(res.data_quality, "差", "超过阈值应被标记为差")
        print(">> 生态环境业务：异常数据识别逻辑通过")

    # --- 3. 游客管理测试 ---
    def test_visitor_flow(self):
        dao = VisitorDAO(self.db)
        visitor_data = {
            "visitor_id": "VIS-001", "visitor_name": "李四",
            "id_card": "110101199001010001", "contact_phone": "13900000000",
            "check_in_method": "线上"
        }
        res_data = {
            "reservation_id": "RES-001", "reservation_date": datetime.date.today(),
            "check_in_period": "上午", "companion_count": 1, "reservation_status": "已确认",
            "ticket_amount": 100, "payment_status": "已支付"
        }
        # 测试预约
        rid = dao.make_reservation(visitor_data, res_data)
        self.assertEqual(rid, "RES-001")

        # 测试流量更新
        dao.update_flow_control("AREA-001", 850)  # 初始0+850，阈值800
        flow = self.db.get(FlowControl, "AREA-001")
        self.assertEqual(flow.current_status, "预警", "超过80%应触发预警")
        print(">> 游客业务：预约与流量预警测试通过")

    # --- 4. 执法监管测试 ---
    def test_enforcement_flow(self):
        dao = EnforcementDAO(self.db)
        # 准备执法者和设备
        ldev = LawEnforceDevice(device_id="LD-001", device_type="记录仪", device_status="正常",
                                last_check_time=datetime.date.today())
        self.db.add(ldev)
        enf = LawEnforcer(enforcer_id="LE-001", enforcer_name="王五", department="执法队",
                          enforcement_permission="全部", contact_phone="110", law_enforce_device_id="LD-001")
        self.db.add(enf)
        self.db.commit()

        # 触发调度
        ill_data = {
            "behavior_id": "IB-001", "behavior_type": "盗猎",
            "occur_time": datetime.datetime.now(), "occur_area_id": "AREA-001",
            "evidence_path": "path/video", "handle_status": "未处理",
            "enforcer_id": "LE-001", "penalty_basis": "法条1"
        }
        disp_data = {
            "dispatch_id": "DIS-001", "enforcer_id": "LE-001",
            "dispatch_time": datetime.datetime.now(), "dispatch_status": "待响应"
        }
        dao.create_dispatch(ill_data, disp_data)
        self.assertIsNotNone(self.db.get(EnforcementDispatch, "DIS-001"))
        print(">> 执法业务：案件记录与调度单生成成功")

    # --- 5. 科研数据支撑测试  ---
    def test_research_flow(self):
        dao = ResearchDAO(self.db)

        # 1. 准备科研人员 (数据字典: tb_researcher_info)
        researcher = ResearcherInfo(
            researcher_id="RE-001",
            researcher_name="钱研究",
            affiliated_unit="中科院",
            research_field="生态修复",
            contact_info="qian@science.cn"
        )
        self.db.add(researcher)
        self.db.commit()

        # 2. 测试立项申请 (数据字典: tb_research_project)
        project_data = {
            "project_id": "RP-TEST-001",
            "project_name": "秦岭生态修复研究",
            "leader_id": "RE-001",
            "application_unit": "中科院",
            "project_start_date": datetime.date.today(),
            "project_end_date": datetime.date.today().replace(year=datetime.date.today().year + 1),
            "project_status": "在研",
            "research_field": "生态修复"
        }

        # 调用 DAO
        dao.add_project(project_data)

        # 验证是否写入成功
        saved_proj = self.db.get(ResearchProject, "RP-TEST-001")
        self.assertIsNotNone(saved_proj)
        self.assertEqual(saved_proj.project_name, "秦岭生态修复研究")
        print(">> 科研业务：项目立项申请测试通过")

if __name__ == '__main__':
    unittest.main()