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


# ==========================================
# 6. 业务模型映射配置 (Refactored)
# ==========================================
# 结构: 'module': {'key': {'model': ModelClass, 'name': '中文名', 'pk': 'primary_key_name'}}
BUSINESS_MODELS = {
    'bio': {
        'record': {'model': MonitorRecord, 'name': '监测记录', 'pk': 'record_id'},
        'species': {'model': SpeciesInfo, 'name': '物种信息', 'pk': 'species_id'},
        'habitat': {'model': HabitatInfo, 'name': '栖息地信息', 'pk': 'habitat_id'},
        'rel': {'model': HabitatSpeciesRel, 'name': '物种-栖息地关联', 'pk': 'rel_id'},
        'device': {'model': MonitorDevice, 'name': '监测设备', 'pk': 'device_id'}
    },
    'env': {
        'data': {'model': EnvironmentData, 'name': '环境监测数据', 'pk': 'data_id'},
        'index': {'model': MonitorIndex, 'name': '监测指标库', 'pk': 'index_id'},
        'device': {'model': MonitorDevice, 'name': '监测设备', 'pk': 'device_id'},
        'area': {'model': AreaInfo, 'name': '区域信息', 'pk': 'area_id'}
    },
    'visitor': {
        'reservation': {'model': ReservationRecord, 'name': '预约记录', 'pk': 'reservation_id'},
        'visitor': {'model': VisitorInfo, 'name': '游客档案', 'pk': 'visitor_id'},
        'track': {'model': VisitorTrack, 'name': '轨迹数据', 'pk': 'track_id'},
        'flow': {'model': FlowControl, 'name': '流量控制', 'pk': 'area_id'}
    },
    'law': {
        'behavior': {'model': IllegalBehavior, 'name': '非法行为记录', 'pk': 'behavior_id'},
        'dispatch': {'model': EnforcementDispatch, 'name': '执法调度单', 'pk': 'dispatch_id'},
        'enforcer': {'model': LawEnforcer, 'name': '执法人员', 'pk': 'enforcer_id'},
        'device': {'model': LawEnforceDevice, 'name': '执法设备', 'pk': 'device_id'},
        'video': {'model': VideoMonitor, 'name': '视频监控点', 'pk': 'monitor_point_id'}
    },
    'research': {
        'project': {'model': ResearchProject, 'name': '科研项目', 'pk': 'project_id'},
        'collect': {'model': ResearchDataCollect, 'name': '数据采集记录', 'pk': 'collect_id'},
        'achievement': {'model': ResearchAchievement, 'name': '科研成果', 'pk': 'achievement_id'},
        'researcher': {'model': ResearcherInfo, 'name': '科研人员', 'pk': 'researcher_id'}
    }
}


# ==========================================
# 7. 通用路由 (处理多表增删)
# ==========================================

@app.route('/generic/<module>/<key>/add', methods=['POST'])
@require_role([ROLE_ADMIN, ROLE_MONITOR, ROLE_ANALYST, ROLE_PARK_MANAGER, ROLE_TECHNICIAN, ROLE_RESEARCHER, ROLE_ENFORCER])
def generic_add(module, key):
    if module not in BUSINESS_MODELS or key not in BUSINESS_MODELS[module]:
        flash('❌ 参数错误：未知的模块或表', 'danger')
        return redirect(url_for(f'{module}_list'))

    target = BUSINESS_MODELS[module][key]
    model_class = target['model']
    
    db = get_db()
    dao = UniversalDAO(db)
    
    try:
        # 简单的数据预处理
        form_data = request.form.to_dict()
        
        # 针对 DateTime/Date 类型的简单转换尝试 (仅做最基础处理，复杂逻辑建议保留在专用API)
        for col in model_class.__table__.columns:
            val = form_data.get(col.name)
            if val:
                if isinstance(col.type, DateTime):
                    try: form_data[col.name] = datetime.datetime.strptime(val, '%Y-%m-%dT%H:%M')
                    except: pass
                elif isinstance(col.type, Date):
                    try: form_data[col.name] = datetime.datetime.strptime(val, '%Y-%m-%d').date()
                    except: pass

        dao.add_record(model_class, form_data)
        flash(f'✅ 已成功添加：{target["name"]}', 'success')
    except Exception as e:
        flash(f'❌ 添加失败: {str(e)}', 'danger')
        # print(e) # Debug
        
    return redirect(url_for(f'{module}_list'))


@app.route('/generic/<module>/<key>/delete/<id>')
@require_role([ROLE_ADMIN])
def generic_delete(module, key, id):
    if module not in BUSINESS_MODELS or key not in BUSINESS_MODELS[module]:
        return redirect(url_for('index'))

    target = BUSINESS_MODELS[module][key]
    db = get_db()
    dao = UniversalDAO(db)
    
    try:
        if dao.delete_record(target['model'], id):
            flash(f'✅ 已删除：{target["name"]}', 'success')
        else:
            flash(f'❌ 删除失败：未找到记录', 'warning')
    except Exception as e:
        flash(f'❌ 删除失败 (可能存在关联数据): {str(e)}', 'danger')
        
    return redirect(url_for(f'{module}_list'))


@app.route('/generic/<module>/<key>/get/<id>')
@require_role([ROLE_ADMIN, ROLE_MONITOR, ROLE_ANALYST, ROLE_PARK_MANAGER, ROLE_TECHNICIAN, ROLE_RESEARCHER, ROLE_ENFORCER])
def generic_get_json(module, key, id):
    """通用：获取单条记录详情 (JSON)"""
    if module not in BUSINESS_MODELS or key not in BUSINESS_MODELS[module]:
        return jsonify({'error': 'Invalid params'}), 400

    target = BUSINESS_MODELS[module][key]
    db = get_db(); dao = UniversalDAO(db)
    
    data = dao.get_record_as_dict(target['model'], id)
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': 'Not found'}), 404


@app.route('/generic/<module>/<key>/update', methods=['POST'])
@require_role([ROLE_ADMIN, ROLE_MONITOR, ROLE_ANALYST, ROLE_PARK_MANAGER, ROLE_TECHNICIAN, ROLE_RESEARCHER, ROLE_ENFORCER])
def generic_update(module, key):
    """通用：提交更新"""
    if module not in BUSINESS_MODELS or key not in BUSINESS_MODELS[module]:
        return redirect(url_for('index'))

    target = BUSINESS_MODELS[module][key]
    model_class = target['model']
    pk_name = target['pk']
    
    form_data = request.form.to_dict()
    pk_value = form_data.get(pk_name) # 必须包含主键
    
    if not pk_value:
        flash('❌ 更新失败：缺少主键', 'danger')
        return redirect(url_for(f'{module}_list'))

    db = get_db(); dao = UniversalDAO(db)
    
    try:
        # 简单的数据预处理 (同 Add)
        for col in model_class.__table__.columns:
            val = form_data.get(col.name)
            if val:
                if isinstance(col.type, DateTime):
                    try: form_data[col.name] = datetime.datetime.strptime(val, '%Y-%m-%dT%H:%M')
                    except: pass
                elif isinstance(col.type, Date):
                    try: form_data[col.name] = datetime.datetime.strptime(val, '%Y-%m-%d').date()
                    except: pass

        if dao.update_record(model_class, pk_value, form_data):
            flash(f'✅ 已更新：{target["name"]}', 'success')
        else:
            flash(f'❌ 更新失败：未找到记录', 'warning')
            
    except Exception as e:
        flash(f'❌ 更新失败: {str(e)}', 'danger')
        
    return redirect(url_for(f'{module}_list'))


# ==========================================
# 8. 业务模块路由 (Refactored to load ALL data)
# ==========================================

@app.route('/')
def index():
    # ... (保持原样)
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
    # 重写 tables_list 以适配新的 BUSINESS_MODELS 结构
    if business_line not in BUSINESS_MODELS:
        return redirect(url_for('index'))
    db = get_db()
    all_data = {}
    
    # 遍历该模块下的所有配置 'key': {'model':...}
    for key, config in BUSINESS_MODELS[business_line].items():
        model = config['model']
        table_name = config['name']
        try:
            records = db.query(model).all()
            headers = [c.name for c in model.__table__.columns]
            all_data[table_name] = {'headers': headers, 'records': records}
        except Exception as e:
            all_data[table_name] = {'headers': ["错误"], 'records': [{"错误": str(e)}]}
            
    return render_template('tables_overview.html', title=business_line.upper() + " 全局概览", business_line=business_line,
                           all_data=all_data)


# --- 生物多样性 (Refactored) ---
@app.route('/bio')
@require_role([ROLE_ADMIN, ROLE_MONITOR, ROLE_ANALYST, ROLE_PARK_MANAGER, ROLE_TECHNICIAN, ROLE_RESEARCHER])
def bio_list():
    db = get_db()
    # 加载所有相关表数据
    data = {
        'records': db.query(MonitorRecord).options(joinedload(MonitorRecord.species_info)).all(),
        'species': db.query(SpeciesInfo).all(),
        'habitats': db.query(HabitatInfo).all(),
        'rels': db.query(HabitatSpeciesRel).options(joinedload(HabitatSpeciesRel.species), joinedload(HabitatSpeciesRel.habitat)).all(),
        'devices': db.query(MonitorDevice).all(),
        # 辅助数据
        'staffs': db.query(StaffInfo).all(),
        'areas': db.query(AreaInfo).all()
    }
    return render_template('bio.html', **data)

# 保留原有的特定路由以兼容旧逻辑，或让其指向 generic?
# 为了保持兼容性，原有的 /bio/add 可以保留，也可以让前端改用 generic。
# 鉴于模板将重写，我们将模板中的 action 改为 generic，这里保留 route 防止报错，但核心逻辑已在 generic。
# 为了代码整洁，这里不再重复定义 bio_add，建议在模板中使用 /generic/bio/record/add


# --- 生态环境 (Refactored) ---
@app.route('/env')
@require_role([ROLE_ADMIN, ROLE_ANALYST, ROLE_RESEARCHER, ROLE_TECHNICIAN, ROLE_PARK_MANAGER])
def env_list():
    db = get_db()
    data = {
        'data_list': db.query(EnvironmentData).options(joinedload(EnvironmentData.index_info), joinedload(EnvironmentData.area_info)).all(),
        'indexes': db.query(MonitorIndex).all(),
        'devices': db.query(MonitorDevice).all(),
        'areas': db.query(AreaInfo).all()
    }
    return render_template('env.html', **data)

@app.route('/env/add', methods=['POST']) # 保留作为特定处理（如自动计算质量）的入口
@require_role([ROLE_ADMIN, ROLE_ANALYST])
def env_add_special():
    # 这是一个特殊逻辑的 Add，不能完全用 Generic 替代（因为包含业务逻辑：判断优/差）
    db = get_db(); dao = EnvironmentDAO(db)
    try:
        data = request.form.to_dict()
        if data.get('collect_time'): data['collect_time'] = datetime.datetime.strptime(data['collect_time'], '%Y-%m-%dT%H:%M')
        dao.add_environment_data(data)
        flash('✅ 上传环境数据成功 (已自动评级)', 'success')
    except Exception as e:
        flash(f'❌ 失败: {e}', 'danger')
    return redirect(url_for('env_list'))


# --- 游客管理 (Refactored) ---
@app.route('/visitor')
@require_role([ROLE_ADMIN, ROLE_PARK_MANAGER, ROLE_ANALYST, ROLE_VISITOR])
def visitor_list():
    db = get_db()
    data = {
        'reservations': db.query(ReservationRecord).options(joinedload(ReservationRecord.visitor)).all(),
        'visitors': db.query(VisitorInfo).all(),
        'tracks': db.query(VisitorTrack).all(),
        'flows': db.query(FlowControl).options(joinedload(FlowControl.area_info)).all(),
        'areas': db.query(AreaInfo).all()
    }
    return render_template('visitor.html', **data)

@app.route('/visitor/add', methods=['POST']) # 保留特殊业务逻辑（预约+游客同时创建）
@require_role([ROLE_ADMIN, ROLE_VISITOR])
def visitor_add_special():
    db = get_db(); dao = VisitorDAO(db)
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
        dao.make_reservation(visitor_data, res_data)
        flash(f'✅ 预约成功: {auto_res_id}', 'success')
    except Exception as e:
        flash(f'❌ 失败: {e}', 'danger')
    return redirect(url_for('visitor_list'))

@app.route('/visitor/cancel/<id>') # 特殊业务逻辑
def visitor_cancel_special(id):
    db = get_db(); dao = VisitorDAO(db)
    dao.cancel_reservation(id)
    return redirect(url_for('visitor_list'))


# --- 执法监管 (Refactored) ---
@app.route('/law')
@require_role([ROLE_ADMIN, ROLE_ENFORCER, ROLE_PARK_MANAGER])
def law_list():
    db = get_db()
    data = {
        'behaviors': db.query(IllegalBehavior).all(),
        'dispatches': db.query(EnforcementDispatch).all(),
        'enforcers': db.query(LawEnforcer).all(),
        'devices': db.query(LawEnforceDevice).all(),
        'videos': db.query(VideoMonitor).all(),
        'areas': db.query(AreaInfo).all()
    }
    return render_template('law.html', **data)

@app.route('/law/add', methods=['POST']) # 保留特殊业务逻辑（行为+调度）
@require_role([ROLE_ADMIN, ROLE_ENFORCER])
def law_add_special():
    db = get_db(); dao = EnforcementDAO(db)
    try:
        # ... (保留原有逻辑)
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
        dao.create_dispatch(ill_data, disp_data)
        flash('✅ 上报成功', 'success')
    except Exception as e:
        flash(f'❌ 失败: {e}', 'danger')
    return redirect(url_for('law_list'))


# --- 科研支撑 (Refactored) ---
@app.route('/research')
@require_role([ROLE_ADMIN, ROLE_RESEARCHER, ROLE_PARK_MANAGER])
def research_list():
    db = get_db()
    data = {
        'projects': db.query(ResearchProject).all(),
        'collects': db.query(ResearchDataCollect).options(joinedload(ResearchDataCollect.project)).all(),
        'achievements': db.query(ResearchAchievement).all(),
        'researchers': db.query(ResearcherInfo).all(),
        'areas': db.query(AreaInfo).all()
    }
    return render_template('research.html', **data)

# Research Add 可以使用 generic，也可以保留 special。这里如果逻辑简单就用 generic。
# 但为了保持一致性，如果原代码有特殊日期转换，建议保留。
# 原代码 research_add 有日期转换，generic_add 已添加基础日期转换，所以可以用 generic_add 替代。
# 但为了安全，我们保留 research_add 作为 /research/add 的 endpoint，或者在模板里指向 /generic/research/project/add


if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')
