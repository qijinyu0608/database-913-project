# 文件名: app.py
import datetime
import hashlib
from functools import wraps
from sqlalchemy import inspect

# 【新增】导入 session
from flask import Flask, render_template, request, redirect, url_for, flash, g, jsonify, session
from db_config import SessionLocal
from models import *
from dao import *
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 生产环境请修改

# ==========================================
# 1. 角色常量定义
# ==========================================
ROLE_ADMIN = '系统管理员'
ROLE_PARK_MANAGER = '公园管理人员'
ROLE_MONITOR = '生态监测员'
ROLE_ANALYST = '数据分析师'
ROLE_VISITOR = '游客'
ROLE_ENFORCER = '执法人员'
ROLE_RESEARCHER = '科研人员'
ROLE_TECHNICIAN = '技术人员'


# ==========================================
# 2. 安全与权限管理模块 (核心修改区)
# ==========================================
class SecurityManager:
    _active_sessions = {}

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def _authenticate_user(db, UserInfoModel, AuthModel, user_id: str, password: str, fixed_role: str = None):
        """
        通用认证逻辑：用于 Staff, Visitor, Enforcer, Researcher。
        :param fixed_role: 如果角色是固定的（如游客/执法人员），则传递；如果是 Staff，则为 None，角色从 StaffInfo.staff_role 取。
        """
        # 1. 动态获取主表和认证表的外键关联字段名
        mapper = inspect(UserInfoModel)
        # 假设所有认证表的主键/外键都与 AuthModel 关联
        id_column_name = mapper.primary_key[0].name  # 获取主键名 (e.g., staff_id, visitor_id)

        # 2. 联表查询：通过主表ID找到用户和其认证信息
        user = db.query(UserInfoModel).join(AuthModel, getattr(UserInfoModel, id_column_name) == getattr(AuthModel,
                                                                                                         id_column_name)).filter(
            getattr(UserInfoModel, id_column_name) == user_id).first()

        if not user or not user.auth:
            return {"success": False, "msg": f"用户 [{user_id}] 不存在或未设置认证信息"}

        auth = user.auth
        if auth.is_locked == 1:
            return {"success": False, "msg": "账号已锁定，请联系管理员"}

        input_hash = SecurityManager.hash_password(password)

        if auth.password_hash == input_hash:
            # 登录成功
            auth.login_fail_count = 0
            auth.last_login_time = datetime.datetime.now()
            db.commit()

            # 动态获取用户名称
            if hasattr(user, 'staff_name'):
                user_name = user.staff_name
            elif hasattr(user, 'visitor_name'):
                user_name = user.visitor_name
            elif hasattr(user, 'enforcer_name'):
                user_name = user.enforcer_name
            elif hasattr(user, 'researcher_name'):
                user_name = user.researcher_name
            else:
                user_name = user_id  # 找不到名字就用ID

            # 确定用户角色
            current_role = fixed_role if fixed_role else user.staff_role

            token = f"token_{user_id}_{datetime.datetime.now().timestamp()}"
            SecurityManager._active_sessions[token] = {
                'user_id': user_id,
                'user_name': user_name,
                'role': current_role,
                'last_action': datetime.datetime.now()
            }
            return {"success": True, "token": token, "role": current_role, "name": user_name}
        else:
            # 登录失败
            auth.login_fail_count += 1
            msg = f"密码错误，剩余尝试次数：{5 - auth.login_fail_count}"

            if auth.login_fail_count >= 5:
                auth.is_locked = 1
                msg = "密码错误次数过多，账号已锁定！"

            db.commit()
            return {"success": False, "msg": msg}

    @staticmethod
    def login(db, user_id: str, password: str):
        """总登录入口：根据 ID 前缀判断用户类型，依次进行验证"""
        user_id = user_id.strip().upper()

        # 1. root 超级管理员
        if user_id == "ROOT":
            if password == "root":
                token = f"token_root_{datetime.datetime.now().timestamp()}"
                SecurityManager._active_sessions[token] = {
                    'user_id': 'root', 'user_name': '超级管理员', 'role': ROLE_ADMIN,
                    'last_action': datetime.datetime.now()
                }
                return {"success": True, "token": token, "role": ROLE_ADMIN, "name": "超级管理员"}
            return {"success": False, "msg": "root 密码错误"}

        # 2. 游客 (假设 ID 前缀为 VI-)
        if user_id.startswith('VI-'):
            return SecurityManager._authenticate_user(
                db, VisitorInfo, VisitorAuth, user_id, password, ROLE_VISITOR)

        # 3. 执法人员 (假设 ID 前缀为 LE-)
        elif user_id.startswith('LE-'):
            return SecurityManager._authenticate_user(
                db, LawEnforcer, EnforcerAuth, user_id, password, ROLE_ENFORCER)

        # 4. 科研人员 (假设 ID 前缀为 RE-)
        elif user_id.startswith('RE-'):
            return SecurityManager._authenticate_user(
                db, ResearcherInfo, ResearcherAuth, user_id, password, ROLE_RESEARCHER)

        # 5. 其他员工 (默认 StaffInfo)
        # 这里需要判断 StaffInfo 是否存在该ID，如果不存在，则返回失败
        try:
            return SecurityManager._authenticate_user(
                db, StaffInfo, StaffAuth, user_id, password)
        except Exception as e:
            # 【核心修改】打印错误堆栈到控制台
            print(f"❌ 登录发生严重错误: {str(e)}")
            import traceback
            traceback.print_exc()

            # 返回包含部分错误信息的提示（方便调试，上线时再改回）
            return {"success": False, "msg": f"系统内部错误: {str(e)}"}

    @staticmethod
    def check_permission(token: str, required_roles: list) -> bool:
        session_data = SecurityManager._active_sessions.get(token)
        if not session_data: return False

        # 超时检查 (30分钟)
        if (datetime.datetime.now() - session_data['last_action']).total_seconds() > 1800:
            del SecurityManager._active_sessions[token]
            return False

        session_data['last_action'] = datetime.datetime.now()
        current_role = session_data['role']

        if current_role == ROLE_ADMIN: return True
        return current_role in required_roles

    @staticmethod
    def get_current_user(token):
        return SecurityManager._active_sessions.get(token)


# --- 权限装饰器 (修改版：从 Session 获取 Token) ---
def require_role(roles: list):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = session.get('token')
            if not token or not SecurityManager.check_permission(token, roles):
                flash('❌ 您的角色权限不足，无法访问此功能', 'danger')
                return redirect(url_for('index'))  # 权限不足回首页
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ==========================================
# 3. 全局拦截与上下文注入 (核心新增)
# ==========================================

# 1. 每次请求前检查登录状态
@app.before_request
def before_request_check():
    # 允许不登录访问的路由（登录页、静态资源、登录逻辑）
    allowed_routes = ['login', 'static', 'do_login']
    if request.endpoint not in allowed_routes and 'token' not in session:
        return redirect(url_for('login'))


# 2. 向所有 HTML 模板注入变量（方便前端判断显示哪个按钮）
@app.context_processor
def inject_user_info():
    token = session.get('token')
    user_info = SecurityManager.get_current_user(token)
    return dict(
        current_user=user_info,
        # 把角色常量也注入进去，方便前端做 if comparison
        ROLE_ADMIN=ROLE_ADMIN,
        ROLE_MONITOR=ROLE_MONITOR,
        ROLE_ANALYST=ROLE_ANALYST,
        ROLE_VISITOR=ROLE_VISITOR,
        ROLE_ENFORCER=ROLE_ENFORCER,
        ROLE_RESEARCHER=ROLE_RESEARCHER,
        ROLE_PARK_MANAGER=ROLE_PARK_MANAGER,
        ROLE_TECHNICIAN=ROLE_TECHNICIAN
    )


# ==========================================
# 4. 登录/登出路由 (核心新增)
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    # POST 登录逻辑
    staff_id = request.form.get('staff_id')
    password = request.form.get('password')

    db = get_db()
    result = SecurityManager.login(db, staff_id, password)

    if result['success']:
        # 登录成功，写入 Session
        session['token'] = result['token']
        session['role'] = result['role']
        flash(f'欢迎回来，{result.get("name", staff_id)}！当前身份：{result["role"]}', 'success')
        return redirect(url_for('index'))
    else:
        flash(f'登录失败: {result["msg"]}', 'danger')
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    token = session.get('token')
    if token and token in SecurityManager._active_sessions:
        del SecurityManager._active_sessions[token]
    session.clear()  # 清空浏览器 Session
    flash('您已安全退出系统', 'info')
    return redirect(url_for('login'))


# ==========================================
# 5. 常规配置与 Jinja2
# ==========================================
def is_datetime_object(obj): return isinstance(obj, datetime.datetime)


def is_date_object(obj): return isinstance(obj, datetime.date) and not isinstance(obj, datetime.datetime)


app.jinja_env.tests['datetime'] = is_datetime_object
app.jinja_env.tests['date'] = is_date_object


def get_db():
    if 'db' not in g: g.db = SessionLocal()
    return g.db


@app.teardown_appcontext
def teardown_db(exception):
    db = g.pop('db', None)
    if db is not None: db.close()


BUSINESS_MODELS = {
    'bio': {'物种信息表 (tb_species_info)': SpeciesInfo, '监测记录表 (tb_monitor_record)': MonitorRecord,
            '栖息地信息表 (tb_habitat_info)': HabitatInfo,
            '物种-栖息地关联表 (tb_habitat_species_rel)': HabitatSpeciesRel,
            '共享监测设备表 (tb_monitor_device)': MonitorDevice, '共享区域信息表 (tb_area_info)': AreaInfo,
            '共享工作人员表 (tb_staff_info)': StaffInfo},
    'env': {'环境监测数据表 (tb_environment_data)': EnvironmentData, '监测指标信息表 (tb_monitor_index)': MonitorIndex,
            '共享监测设备表 (tb_monitor_device)': MonitorDevice, '共享区域信息表 (tb_area_info)': AreaInfo},
    'visitor': {'预约记录表 (tb_reservation_record)': ReservationRecord, '游客信息表 (tb_visitor_info)': VisitorInfo,
                '游客轨迹数据表 (tb_visitor_track)': VisitorTrack, '流量控制信息表 (tb_flow_control)': FlowControl,
                '共享区域信息表 (tb_area_info)': AreaInfo},
    'law': {'非法行为记录表 (tb_illegal_behavior)': IllegalBehavior,
            '执法调度信息表 (tb_enforcement_dispatch)': EnforcementDispatch,
            '执法人员信息表 (tb_law_enforcer)': LawEnforcer, '视频监控点信息表 (tb_video_monitor)': VideoMonitor,
            '共享执法设备表 (tb_law_enforce_device)': LawEnforceDevice, '共享区域信息表 (tb_area_info)': AreaInfo,
            '共享工作人员表 (tb_staff_info)': StaffInfo},
    'research': {'科研项目信息表 (tb_research_project)': ResearchProject,
                 '科研数据采集记录表 (tb_research_data_collect)': ResearchDataCollect,
                 '科研成果信息表 (tb_research_achievement)': ResearchAchievement,
                 '共享科研人员表 (tb_researcher_info)': ResearcherInfo, '共享区域信息表 (tb_area_info)': AreaInfo}
}


# ==========================================
# 6. 业务路由 (已全部保留并应用权限)
# ==========================================

@app.route('/')
def index():
    # 首页不需要强制权限检查，因为 before_request 已经保证了必须登录
    db = get_db()
    try:
        bio_count = db.query(MonitorRecord).count()
        env_count = db.query(EnvironmentData).count()
        visitor_count = db.query(ReservationRecord).count()
        law_count = db.query(IllegalBehavior).count()
        research_count = db.query(ResearchProject).count()
    except Exception:
        bio_count = env_count = visitor_count = law_count = research_count = 0
    return render_template('index.html', bio_count=bio_count, env_count=env_count, visitor_count=visitor_count,
                           law_count=law_count, research_count=research_count)


@app.route('/tables/<business_line>')
def tables_list(business_line):
    if business_line not in BUSINESS_MODELS:
        return redirect(url_for('index'))
    db = get_db()
    all_data = {}
    for table_name, model in BUSINESS_MODELS[business_line].items():
        try:
            records = db.query(model).options(joinedload('*')).all()
            headers = [c.name for c in model.__table__.columns]
            all_data[table_name] = {'headers': headers, 'records': records}
        except Exception as e:
            all_data[table_name] = {'headers': ["错误"], 'records': [{"错误": str(e)}]}
    return render_template('tables_overview.html', title=business_line.upper() + " 概览", business_line=business_line,
                           all_data=all_data)


# --- 生物多样性 ---
@app.route('/bio')
@require_role([ROLE_ADMIN, ROLE_MONITOR, ROLE_ANALYST, ROLE_PARK_MANAGER, ROLE_TECHNICIAN, ROLE_RESEARCHER])
def bio_list():
    db = get_db()
    records = db.query(MonitorRecord).options(joinedload(MonitorRecord.species_info),
                                              joinedload(MonitorRecord.device_info)).all()
    species_list = db.query(SpeciesInfo).all();
    devices = db.query(MonitorDevice).all();
    staffs = db.query(StaffInfo).all()
    return render_template('bio.html', records=records, species=species_list, devices=devices, staffs=staffs)


@app.route('/bio/add', methods=['POST'])
@require_role([ROLE_ADMIN, ROLE_MONITOR])
def bio_add():
    db = get_db();
    dao = BioDiversityDAO(db)
    try:
        data = request.form.to_dict()
        if data.get('monitor_time'): data['monitor_time'] = datetime.datetime.strptime(data['monitor_time'],
                                                                                       '%Y-%m-%dT%H:%M')
        data['data_status'] = '待核实'
        dao.add_monitor_record(data);
        db.commit();
        flash('✅ 添加成功', 'success')
    except Exception as e:
        db.rollback(); flash(f'❌ 失败: {e}', 'danger')
    return redirect(url_for('bio_list'))


@app.route('/bio/delete/<id>')
@require_role([ROLE_ADMIN])
def bio_delete(id):
    db = get_db();
    dao = BioDiversityDAO(db)
    if dao.delete_record(id):
        db.commit(); flash('✅ 删除成功', 'success')
    else:
        flash('❌ 未找到', 'danger')
    return redirect(url_for('bio_list'))


# --- 生态环境 ---
@app.route('/env')
@require_role([ROLE_ADMIN, ROLE_ANALYST, ROLE_RESEARCHER, ROLE_TECHNICIAN, ROLE_PARK_MANAGER])
def env_list():
    db = get_db()
    data_list = db.query(EnvironmentData).all()
    indexes = db.query(MonitorIndex).all();
    devices = db.query(MonitorDevice).all();
    areas = db.query(AreaInfo).all()
    return render_template('env.html', data_list=data_list, indexes=indexes, devices=devices, areas=areas)


@app.route('/env/add', methods=['POST'])
@require_role([ROLE_ADMIN, ROLE_ANALYST])
def env_add():
    db = get_db();
    dao = EnvironmentDAO(db)
    try:
        data = request.form.to_dict()
        if data.get('collect_time'): data['collect_time'] = datetime.datetime.strptime(data['collect_time'],
                                                                                       '%Y-%m-%dT%H:%M')
        dao.add_environment_data(data);
        db.commit();
        flash('✅ 上传成功', 'success')
    except Exception as e:
        db.rollback(); flash(f'❌ 失败: {e}', 'danger')
    return redirect(url_for('env_list'))


@app.route('/env/delete/<id>')
@require_role([ROLE_ADMIN])
def env_delete(id):
    db = get_db();
    dao = EnvironmentDAO(db)
    if dao.delete_data(id):
        db.commit(); flash('✅ 删除成功', 'success')
    else:
        flash('❌ 失败', 'danger')
    return redirect(url_for('env_list'))


# --- 游客管理 ---
@app.route('/visitor')
@require_role([ROLE_ADMIN, ROLE_PARK_MANAGER, ROLE_ANALYST, ROLE_VISITOR])
def visitor_list():
    db = get_db()
    reservations = db.query(ReservationRecord).options(joinedload(ReservationRecord.visitor)).all()
    area_status = db.query(FlowControl).options(joinedload(FlowControl.area_info)).all()
    return render_template('visitor.html', reservations=reservations, area_status=area_status)


@app.route('/visitor/add', methods=['POST'])
@require_role([ROLE_ADMIN, ROLE_VISITOR])
def visitor_add():
    db = get_db();
    dao = VisitorDAO(db)
    try:
        now = datetime.datetime.now()
        auto_res_id = f"RR-{now.strftime('%Y%m%d-%H%M%S')}"
        raw_count = int(request.form.get('companion_count', 0))
        visitor_data = {
            'visitor_id': request.form.get('visitor_id'), 'visitor_name': request.form.get('visitor_name'),
            'id_card': request.form.get('id_card'), 'contact_phone': request.form.get('contact_phone'),
            'check_in_method': '线上预约'
        }
        res_data = {
            'reservation_id': auto_res_id,
            'reservation_date': datetime.datetime.strptime(request.form.get('reservation_date'), '%Y-%m-%d').date(),
            'check_in_period': request.form.get('check_in_period'), 'companion_count': raw_count,
            'reservation_status': '已确认',
            'ticket_amount': (1 + raw_count) * 100.0, 'payment_status': '已支付'
        }
        dao.make_reservation(visitor_data, res_data);
        db.commit();
        flash(f'✅ 预约成功: {auto_res_id}', 'success')
    except Exception as e:
        db.rollback(); flash(f'❌ 失败: {e}', 'danger')
    return redirect(url_for('visitor_list'))


@app.route('/visitor/cancel/<id>')
@require_role([ROLE_ADMIN, ROLE_PARK_MANAGER, ROLE_VISITOR])
def visitor_cancel(id):
    db = get_db();
    dao = VisitorDAO(db)
    if dao.cancel_reservation(id):
        db.commit(); flash('✅ 已取消', 'warning')
    else:
        flash('❌ 失败', 'danger')
    return redirect(url_for('visitor_list'))


# --- 执法监管 ---
@app.route('/law')
@require_role([ROLE_ADMIN, ROLE_ENFORCER, ROLE_PARK_MANAGER])
def law_list():
    db = get_db()
    behaviors = db.query(IllegalBehavior).all();
    enforcers = db.query(LawEnforcer).all();
    areas = db.query(AreaInfo).all()
    return render_template('law.html', behaviors=behaviors, enforcers=enforcers, areas=areas)


@app.route('/law/add', methods=['POST'])
@require_role([ROLE_ADMIN, ROLE_ENFORCER])
def law_add():
    db = get_db();
    dao = EnforcementDAO(db)
    try:
        now = datetime.datetime.now()
        date_str = now.strftime('%Y%m%d')
        behavior_id = request.form.get('behavior_id')
        id_suffix = behavior_id.split('-')[-1] if '-' in behavior_id else '0001'
        ill_data = {
            'behavior_id': behavior_id, 'behavior_type': request.form.get('behavior_type'),
            'occur_time': datetime.datetime.strptime(request.form.get('occur_time'), '%Y-%m-%dT%H:%M'),
            'occur_area_id': request.form.get('occur_area_id'), 'evidence_path': request.form.get('evidence_path'),
            'handle_status': '未处理', 'enforcer_id': request.form.get('enforcer_id'),
            'penalty_basis': request.form.get('penalty_basis')
        }
        disp_data = {
            'dispatch_id': f"ED-{date_str}-{id_suffix}", 'enforcer_id': request.form.get('enforcer_id'),
            'dispatch_time': now, 'dispatch_status': '已派单'
        }
        dao.create_dispatch(ill_data, disp_data);
        db.commit();
        flash('✅ 上报成功', 'success')
    except Exception as e:
        db.rollback(); flash(f'❌ 失败: {e}', 'danger')
    return redirect(url_for('law_list'))


# --- 科研支撑 ---
@app.route('/research')
@require_role([ROLE_ADMIN, ROLE_RESEARCHER, ROLE_PARK_MANAGER])
def research_list():
    db = get_db()
    projects = db.query(ResearchProject).all();
    researchers = db.query(ResearcherInfo).all()
    return render_template('research.html', projects=projects, researchers=researchers)


@app.route('/research/add', methods=['POST'])
@require_role([ROLE_ADMIN, ROLE_RESEARCHER])
def research_add():
    db = get_db();
    dao = ResearchDAO(db)
    try:
        data = request.form.to_dict()
        data['project_start_date'] = datetime.datetime.strptime(data['project_start_date'], '%Y-%m-%d').date()
        data['project_end_date'] = datetime.datetime.strptime(data['project_end_date'], '%Y-%m-%d').date()
        dao.add_project(data);
        db.commit();
        flash('✅ 立项成功', 'success')
    except Exception as e:
        db.rollback(); flash(f'❌ 失败: {e}', 'danger')
    return redirect(url_for('research_list'))


@app.route('/research/delete/<id>')
@require_role([ROLE_ADMIN])
def research_delete(id):
    db = get_db();
    dao = ResearchDAO(db)
    if dao.delete_project(id):
        db.commit(); flash('✅ 删除成功', 'success')
    else:
        flash('❌ 失败', 'danger')
    return redirect(url_for('research_list'))


if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')