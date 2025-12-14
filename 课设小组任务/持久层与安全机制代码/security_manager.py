import hashlib
import datetime
from sqlalchemy.orm import Session
from models import StaffInfo, StaffAuth


class SecurityManager:
    # 内存缓存：仅用于存储登录成功后的 Token 会话
    _active_sessions = {}

    @staticmethod
    def hash_password(password: str) -> str:
        """使用 SHA-256 算法加密密码"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def login(db: Session, staff_id: str, password: str):
        """
        真正的数据库登录逻辑：
        1. 联表查询：同时获取员工基本信息和认证信息
        2. 锁定检查：检查 login_fail_count 和 is_locked
        3. 密码比对：比对数据库中的 password_hash
        """
        # 1. 联表查询 (Inner Join 确保必须两张表都有数据)
        user = db.query(StaffInfo).join(StaffAuth).filter(StaffInfo.staff_id == staff_id).first()

        if not user:
            return {"success": False, "msg": "用户不存在"}

        # 通过 ORM 关系直接获取认证对象
        auth = user.auth
        if not auth:
            return {"success": False, "msg": "该用户未激活认证信息(tb_staff_auth缺失)"}

        # 2. 检查锁定状态
        if auth.is_locked == 1:
            return {"success": False, "msg": "账号已锁定，请联系管理员解锁"}

        # 3. 验证密码
        input_hash = SecurityManager.hash_password(password)

        if auth.password_hash == input_hash:
            # --- 登录成功 ---
            # 重置失败计数，更新最后登录时间
            auth.login_fail_count = 0
            auth.last_login_time = datetime.datetime.now()
            db.commit()  # 提交更改到数据库

            # 生成会话 Token
            token = f"token_{staff_id}_{datetime.datetime.now().timestamp()}"
            SecurityManager._active_sessions[token] = {
                'user_id': staff_id,
                'role': user.staff_role,
                'last_action': datetime.datetime.now()
            }
            return {"success": True, "token": token, "role": user.staff_role}
        else:
            # --- 登录失败 ---
            # 增加失败计数
            auth.login_fail_count += 1
            msg = f"密码错误，剩余次数：{5 - auth.login_fail_count}"

            # 检查是否达到锁定阈值
            if auth.login_fail_count >= 5:
                auth.is_locked = 1
                msg = "密码错误次数过多，账号已锁定！"

            db.commit()  # 必须提交，否则失败次数不会被记录
            return {"success": False, "msg": msg}

    @staticmethod
    def check_permission(token: str, required_roles: list) -> bool:
        """RBAC 权限检查 (带30分钟超时)"""
        session = SecurityManager._active_sessions.get(token)
        if not session:
            return False

        # 30分钟会话超时检查
        now = datetime.datetime.now()
        if (now - session['last_action']).total_seconds() > 1800:
            del SecurityManager._active_sessions[token]  # 移除过期会话
            return False

        # 刷新活跃时间
        session['last_action'] = now

        # 角色检查
        current_role = session['role']
        if "系统管理员" in current_role:
            return True  # 管理员拥有所有权限
        return current_role in required_roles