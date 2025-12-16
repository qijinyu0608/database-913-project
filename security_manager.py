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
        登录逻辑（支持 root 高权限用户）：
        1. 特殊处理 root 用户（无需数据库记录，直接验证密码）
        2. 普通用户：联表查询 + 锁定检查 + 密码比对
        """
        # 处理 root 高权限用户登录
        if staff_id == "root":
            # root 密码固定为 "root"（实际生产环境需加密存储）
            if password == "root":
                token = f"token_root_{datetime.datetime.now().timestamp()}"
                SecurityManager._active_sessions[token] = {
                    'user_id': 'root',
                    'role': '系统管理员',  # root 拥有系统管理员权限
                    'last_action': datetime.datetime.now()
                }
                return {"success": True, "token": token, "role": "系统管理员"}
            else:
                return {"success": False, "msg": "root 密码错误"}

        # 普通员工登录逻辑
        user = db.query(StaffInfo).join(StaffAuth).filter(StaffInfo.staff_id == staff_id).first()

        if not user:
            return {"success": False, "msg": "用户不存在"}

        auth = user.auth
        if not auth:
            return {"success": False, "msg": "该用户未激活认证信息(tb_staff_auth缺失)"}

        if auth.is_locked == 1:
            return {"success": False, "msg": "账号已锁定，请联系管理员解锁"}

        input_hash = SecurityManager.hash_password(password)

        if auth.password_hash == input_hash:
            # 登录成功：重置失败计数，更新登录时间
            auth.login_fail_count = 0
            auth.last_login_time = datetime.datetime.now()
            db.commit()

            token = f"token_{staff_id}_{datetime.datetime.now().timestamp()}"
            SecurityManager._active_sessions[token] = {
                'user_id': staff_id,
                'role': user.staff_role,
                'last_action': datetime.datetime.now()
            }
            return {"success": True, "token": token, "role": user.staff_role}
        else:
            # 登录失败：增加失败计数，检查锁定条件
            auth.login_fail_count += 1
            msg = f"密码错误，剩余次数：{5 - auth.login_fail_count}"

            if auth.login_fail_count >= 5:
                auth.is_locked = 1
                msg = "密码错误次数过多，账号已锁定！"

            db.commit()
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

        # 角色检查：root 拥有所有权限（因 role 设为系统管理员，已包含在原有逻辑中）
        current_role = session['role']
        if "系统管理员" in current_role:
            return True  # 管理员拥有所有权限
        return current_role in required_roles