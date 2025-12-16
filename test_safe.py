import unittest
import datetime
from db_config import SessionLocal
from models import StaffInfo, MonitorRecord, SpeciesInfo, StaffAuth
from security_manager import SecurityManager
from dao import BioDiversityDAO


class TestNationalParkPersistence(unittest.TestCase):

    def setUp(self):
        """测试前准备：初始化数据库连接和基础测试数据"""
        self.db = SessionLocal()
        self.dao = BioDiversityDAO(self.db)

        # 定义测试常量 (符合数据库约束格式)
        self.test_staff_id = "STAFF-2025-9999"
        self.test_password = "User@9999"  # 密码格式
        self.test_species_id = "SP-2025-9999"
        self.test_device_id = "MD-2025-0009"  # 真实存在的红外相机
        self.test_area_id = "AREA-2025-0005"  # 该设备所属的区域

        # 1. 确保【测试物种】存在 (避免外键报错)
        species = self.db.get(SpeciesInfo, self.test_species_id)
        if not species:
            species = SpeciesInfo(
                species_id=self.test_species_id,
                species_name_cn="测试物种",
                species_name_latin="Test Species",
                species_category="测试科",
                protection_level="无"
            )
            self.db.add(species)
            self.db.commit()

        # 2. 确保【测试员工基本信息】存在 (tb_staff_info)
        user = self.db.get(StaffInfo, self.test_staff_id)
        if not user:
            user = StaffInfo(
                staff_id=self.test_staff_id,
                staff_name="测试员",
                staff_role="生态监测员",
                department="自动化测试组",
                contact_phone="13800009999"
            )
            self.db.add(user)
            self.db.commit()

        # 3. 确保【测试员工认证信息】存在 (tb_staff_auth)
        auth = self.db.get(StaffAuth, self.test_staff_id)
        if not auth:
            pwd_hash = SecurityManager.hash_password(self.test_password)
            auth = StaffAuth(
                staff_id=self.test_staff_id,
                password_hash=pwd_hash,
                login_fail_count=0,
                is_locked=0
            )
            self.db.add(auth)
            self.db.commit()
        else:
            # 重置状态以便重新测试
            auth.is_locked = 0
            auth.login_fail_count = 0
            self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_login_flow(self):
        print(f"\n--- 测试普通用户登录流程 (密码: {self.test_password}) ---")

        # 1. 成功登录测试
        res = SecurityManager.login(self.db, self.test_staff_id, self.test_password)
        self.assertTrue(res['success'], "正确密码应登录成功")
        print(f"登录成功，Token: {res.get('token')}")

        # 2. 失败锁定测试
        print("正在模拟5次密码错误...")
        for i in range(5):
            res_fail = SecurityManager.login(self.db, self.test_staff_id, "wrong_password")
            if i == 4:
                self.assertIn("锁定", res_fail['msg'])
            else:
                self.assertFalse(res_fail['success'])

        # 3. 验证锁定后无法登录
        res_locked = SecurityManager.login(self.db, self.test_staff_id, self.test_password)
        self.assertFalse(res_locked['success'], "账号锁定后，即使密码正确也应拒绝登录")
        print("锁定机制验证通过")

    def test_root_login(self):
        """测试 root 高权限用户登录"""
        print("\n--- 测试 root 用户登录 ---")

        # 1. 正确密码登录
        res_success = SecurityManager.login(self.db, "root", "root")
        self.assertTrue(res_success['success'], "root 正确密码应登录成功")
        self.assertEqual(res_success['role'], "系统管理员", "root 应拥有系统管理员权限")
        print(f"root 登录成功，Token: {res_success.get('token')}")

        # 2. 错误密码登录
        res_fail = SecurityManager.login(self.db, "root", "wrong_password")
        self.assertFalse(res_fail['success'])
        self.assertIn("密码错误", res_fail['msg'])
        print("root 密码验证机制通过")

    def test_root_permission(self):
        """测试 root 用户权限"""
        print("\n--- 测试 root 用户权限 ---")

        # 1. root 登录获取 Token
        res = SecurityManager.login(self.db, "root", "root")
        root_token = res['token']

        # 2. 验证 root 可访问所有角色权限
        self.assertTrue(SecurityManager.check_permission(root_token, ["生态监测员"]))
        self.assertTrue(SecurityManager.check_permission(root_token, ["公园管理人员"]))
        self.assertTrue(SecurityManager.check_permission(root_token, ["系统管理员"]))
        print("root 用户拥有所有权限，验证通过")

    def test_session_timeout(self):
        print("\n--- 测试会话超时控制 (30分钟自动退出) ---")

        # 1. 普通用户登录
        res = SecurityManager.login(self.db, self.test_staff_id, self.test_password)
        self.assertTrue(res['success'], "登录失败，无法继续测试超时")
        token = res['token']
        print(f"登录成功，获取 Token: {token}")

        # 2. 验证当前权限有效
        is_active = SecurityManager.check_permission(token, ["生态监测员"])
        self.assertTrue(is_active, "刚登录的会话应该是有效的")
        print("当前状态：会话有效")

        # 3. 模拟31分钟未操作（超时）
        past_time = datetime.datetime.now() - datetime.timedelta(minutes=31)
        SecurityManager._active_sessions[token]['last_action'] = past_time
        print(f"模拟时间流逝：手动将最后操作时间修改为 31 分钟前 ({past_time.strftime('%H:%M:%S')})")

        # 4. 验证超时后权限失效
        is_active_after_timeout = SecurityManager.check_permission(token, ["生态监测员"])
        self.assertFalse(is_active_after_timeout, "超过30分钟未操作，权限检查应返回 False")

        # 5. 验证 Token 已被清除
        self.assertNotIn(token, SecurityManager._active_sessions, "超时后 Token 应被系统自动清除")
        print("测试通过：会话已自动销毁，用户被迫下线。")


if __name__ == '__main__':
    unittest.main()