from flask import Flask, render_template, request, redirect, url_for, flash, g
from db_config import SessionLocal
from models import *
from dao import *
import datetime
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# --- 核心修复：注册 Jinja2 测试器 ---

def is_datetime_object(obj):
    """用于检查对象是否是 datetime.datetime 对象"""
    return isinstance(obj, datetime.datetime)

def is_date_object(obj):
    """用于检查对象是否是 datetime.date 对象，但排除 datetime.datetime"""
    # 排除 datetime.datetime，只保留纯 date 对象
    return isinstance(obj, datetime.date) and not isinstance(obj, datetime.datetime)

# 注册 'datetime' 测试器
app.jinja_env.tests['datetime'] = is_datetime_object
# 注册 'date' 测试器 (解决当前报错)
app.jinja_env.tests['date'] = is_date_object

# ==========================================
# 共享逻辑：数据库连接管理
# ==========================================
def get_db():
    if 'db' not in g:
        g.db = SessionLocal()
    return g.db


@app.teardown_appcontext
def teardown_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ==========================================
# 核心修复点：业务概览所需的核心表映射 (已包含您列出的所有表)
# ==========================================
BUSINESS_MODELS = {
    'bio': {
        '物种信息表 (tb_species_info)': SpeciesInfo,
        '监测记录表 (tb_monitor_record)': MonitorRecord,
        '栖息地信息表 (tb_habitat_info)': HabitatInfo,
        '物种-栖息地关联表 (tb_habitat_species_rel)': HabitatSpeciesRel,
        '共享监测设备表 (tb_monitor_device)': MonitorDevice,
        '共享区域信息表 (tb_area_info)': AreaInfo,
        '共享工作人员表 (tb_staff_info)': StaffInfo,
    },
    'env': {
        '环境监测数据表 (tb_environment_data)': EnvironmentData,
        '监测指标信息表 (tb_monitor_index)': MonitorIndex,
        '共享监测设备表 (tb_monitor_device)': MonitorDevice,
        '共享区域信息表 (tb_area_info)': AreaInfo,
    },
    'visitor': {
        '预约记录表 (tb_reservation_record)': ReservationRecord,
        '游客信息表 (tb_visitor_info)': VisitorInfo,
        '游客轨迹数据表 (tb_visitor_track)': VisitorTrack,
        '流量控制信息表 (tb_flow_control)': FlowControl,
        '共享区域信息表 (tb_area_info)': AreaInfo,
    },
    'law': {
        '非法行为记录表 (tb_illegal_behavior)': IllegalBehavior,
        '执法调度信息表 (tb_enforcement_dispatch)': EnforcementDispatch,
        '执法人员信息表 (tb_law_enforcer)': LawEnforcer,
        '视频监控点信息表 (tb_video_monitor)': VideoMonitor,
        '共享执法设备表 (tb_law_enforce_device)': LawEnforceDevice,
        '共享区域信息表 (tb_area_info)': AreaInfo,
        '共享工作人员表 (tb_staff_info)': StaffInfo,
    },
    'research': {
        '科研项目信息表 (tb_research_project)': ResearchProject,
        '科研数据采集记录表 (tb_research_data_collect)': ResearchDataCollect,
        '科研成果信息表 (tb_research_achievement)': ResearchAchievement,
        '共享科研人员表 (tb_researcher_info)': ResearcherInfo,
        '共享区域信息表 (tb_area_info)': AreaInfo,
    }
}


# 首页路由
@app.route('/')
def index():
    db = get_db()
    try:
        bio_count = db.query(MonitorRecord).count()
        env_count = db.query(EnvironmentData).count()
        visitor_count = db.query(ReservationRecord).count()
        law_count = db.query(IllegalBehavior).count()
        research_count = db.query(ResearchProject).count()
    except Exception as e:
        flash(f'数据统计加载失败: {str(e)}', 'warning')
        bio_count = env_count = visitor_count = law_count = research_count = 0
    return render_template(
        'index.html',
        bio_count=bio_count,
        env_count=env_count,
        visitor_count=visitor_count,
        law_count=law_count,
        research_count=research_count
    )


# ==========================================
# 核心修复路由：业务概览 (展示所有表)
# ==========================================
@app.route('/tables/<business_line>')
def tables_list(business_line):
    if business_line not in BUSINESS_MODELS:
        flash('❌ 业务线不存在！', 'danger')
        return redirect(url_for('index'))

    db = get_db()
    all_data = {}

    for table_name, model in BUSINESS_MODELS[business_line].items():
        try:
            # 使用 joinedload('*') 强制加载所有关联数据，增强通用页面的健壮性
            records = db.query(model).options(joinedload('*')).all()

            headers = [c.name for c in model.__table__.columns]

            all_data[table_name] = {
                'headers': headers,
                'records': records
            }
        except Exception as e:
            # 捕获查询错误，打印到控制台进行排查
            print(f"❌ 警告：查询 {table_name} 失败: {e}")
            all_data[table_name] = {
                'headers': ["错误"],
                'records': [{"错误": f"数据加载失败，请检查模型关系或数据完整性: {str(e)}."}]
            }

    context = {
        'title': business_line.upper() + " 业务概览",
        'business_line': business_line,
        'all_data': all_data
    }
    # 确保您有 tables_overview.html 模板
    return render_template('tables_overview.html', **context)


# ==========================================
# 生物多样性模块 (CRUD 页面)
# ==========================================
@app.route('/bio')
def bio_list():
    db = get_db()
    try:
        # 修复点：使用 joinedload 预加载关联的物种信息 (species_info) 和设备信息
        records = db.query(MonitorRecord).options(
            joinedload(MonitorRecord.species_info),
            joinedload(MonitorRecord.device_info)
        ).all()

        species_list = db.query(SpeciesInfo).all()
        devices = db.query(MonitorDevice).all()
        staffs = db.query(StaffInfo).all()
        app.logger.info(f"查询到生物监测记录: {len(records)} 条")
    except Exception as e:
        flash(f'生物多样性数据加载失败: {str(e)}', 'danger')
        records = []
        species_list = []
        devices = []
        staffs = []
    return render_template(
        'bio.html',
        records=records,
        species=species_list,
        devices=devices,
        staffs=staffs
    )


@app.route('/bio/add', methods=['POST'])
def bio_add():
    db = get_db()
    dao = BioDiversityDAO(db)
    try:
        data = request.form.to_dict()
        if 'monitor_time' in data and data['monitor_time']:
            data['monitor_time'] = datetime.datetime.strptime(
                data['monitor_time'], '%Y-%m-%dT%H:%M'
            )
        data['data_status'] = '待核实'
        dao.add_monitor_record(data)
        db.commit()
        flash('✅ 监测记录添加成功！', 'success')
    except Exception as e:
        db.rollback()
        flash(f'❌ 添加失败: {str(e)}', 'danger')
        app.logger.error(f'生物数据添加错误: {str(e)}')
    return redirect(url_for('bio_list'))


@app.route('/bio/delete/<id>')
def bio_delete(id):
    db = get_db()
    dao = BioDiversityDAO(db)
    try:
        if dao.delete_record(id):
            db.commit()
            flash('✅ 删除成功', 'success')
        else:
            flash('❌ 未找到对应记录', 'danger')
    except Exception as e:
        db.rollback()
        flash(f'❌ 删除失败: {str(e)}', 'danger')
        app.logger.error(f'生物数据删除错误: {str(e)}')
    return redirect(url_for('bio_list'))


@app.route('/env')
def env_list():
    db = get_db()
    try:
        data_list = db.query(EnvironmentData).options(
            joinedload(EnvironmentData.index_info),
            joinedload(EnvironmentData.area_info)
        ).all()
        indexes = db.query(MonitorIndex).all()
        devices = db.query(MonitorDevice).all()
        areas = db.query(AreaInfo).all()
        app.logger.info(f"查询到环境数据: {len(data_list)} 条")
    except Exception as e:
        flash(f'环境数据加载失败: {str(e)}', 'danger')
        data_list = []
        indexes = []
        devices = []
        areas = []
    return render_template(
        'env.html',
        data_list=data_list,
        indexes=indexes,
        devices=devices,
        areas=areas
    )


@app.route('/env/add', methods=['POST'])
def env_add():
    db = get_db()
    dao = EnvironmentDAO(db)
    try:
        data = request.form.to_dict()
        if 'collect_time' in data and data['collect_time']:
            data['collect_time'] = datetime.datetime.strptime(
                data['collect_time'], '%Y-%m-%dT%H:%M'
            )
        dao.add_environment_data(data)
        db.commit()
        flash('✅ 环境数据上传成功', 'success')
    except Exception as e:
        db.rollback()
        flash(f'❌ 上传失败: {str(e)}', 'danger')
        app.logger.error(f'环境数据添加错误: {str(e)}')
    return redirect(url_for('env_list'))


@app.route('/env/delete/<id>')
def env_delete(id):
    db = get_db()
    dao = EnvironmentDAO(db)
    try:
        if dao.delete_data(id):
            db.commit()
            flash('✅ 删除成功', 'success')
        else:
            flash('❌ 未找到对应记录', 'danger')
    except Exception as e:
        db.rollback()
        flash(f'❌ 删除失败: {str(e)}', 'danger')
        app.logger.error(f'环境数据删除错误: {str(e)}')
    return redirect(url_for('env_list'))


@app.route('/visitor')
def visitor_list():
    db = get_db()
    try:
        reservations = db.query(ReservationRecord).options(
            joinedload(ReservationRecord.visitor)
        ).all()
        area_status = db.query(FlowControl).options(
            joinedload(FlowControl.area_info)
        ).all()
        app.logger.info(f"查询到预约记录: {len(reservations)} 条")
    except Exception as e:
        flash(f'游客数据加载失败: {str(e)}', 'danger')
        reservations = []
        area_status = []
    return render_template(
        'visitor.html',
        reservations=reservations,
        area_status=area_status
    )


@app.route('/visitor/add', methods=['POST'])
def visitor_add():
    db = get_db()
    dao = VisitorDAO(db)
    try:
        # 1. 自动生成唯一 ID (保留之前的修复)
        now = datetime.datetime.now()
        auto_res_id = f"RR-{now.strftime('%Y%m%d-%H%M%S')}"

        # 2. 获取并处理同行人数
        # 如果前端传空，默认为 0
        raw_count = request.form.get('companion_count', 0)
        try:
            companion_count = int(raw_count)
        except ValueError:
            companion_count = 0

        # 3. 计算总票价
        # 总人数 = 1 (本人) + 同行人数
        # 单价 = 100
        total_price = (1 + companion_count) * 100.0

        visitor_data = {
            'visitor_id': request.form.get('visitor_id'),
            'visitor_name': request.form.get('visitor_name'),
            'id_card': request.form.get('id_card'),
            'contact_phone': request.form.get('contact_phone'),
            'check_in_method': '线上预约'
        }

        res_data = {
            'reservation_id': auto_res_id,
            'reservation_date': datetime.datetime.strptime(request.form.get('reservation_date'), '%Y-%m-%d').date(),
            'check_in_period': request.form.get('check_in_period'),
            'companion_count': companion_count,
            'reservation_status': '已确认',

            # 【核心修改点】使用计算后的总价格
            'ticket_amount': total_price,

            'payment_status': '已支付'
        }

        dao.make_reservation(visitor_data, res_data)
        db.commit()

        flash(f'✅ 预约成功！总人数: {1 + companion_count}人，总金额: ￥{total_price}，单号: {auto_res_id}', 'success')

    except Exception as e:
        db.rollback()
        if "PRIMARY KEY" in str(e):
            flash('❌ 提交失败：系统繁忙，请重试。', 'danger')
        else:
            flash(f'❌ 预约失败: {str(e)}', 'danger')
        app.logger.error(f'游客预约错误: {str(e)}')

    return redirect(url_for('visitor_list'))


@app.route('/visitor/cancel/<id>')
def visitor_cancel(id):
    db = get_db()
    dao = VisitorDAO(db)
    try:
        if dao.cancel_reservation(id):
            db.commit()
            flash('✅ 预约已取消', 'warning')
        else:
            flash('❌ 未找到对应预约', 'danger')
    except Exception as e:
        db.rollback()
        flash(f'❌ 操作失败: {str(e)}', 'danger')
        app.logger.error(f'预约取消错误: {str(e)}')
    return redirect(url_for('visitor_list'))


@app.route('/law')
def law_list():
    db = get_db()
    try:
        behaviors = db.query(IllegalBehavior).options(
            joinedload(IllegalBehavior.occur_area_info),
            joinedload(IllegalBehavior.handling_enforcer)
        ).all()
        enforcers = db.query(LawEnforcer).all()
        areas = db.query(AreaInfo).all()
        app.logger.info(f"查询到违法记录: {len(behaviors)} 条")
    except Exception as e:
        flash(f'执法数据加载失败: {str(e)}', 'danger')
        behaviors = []
        enforcers = []
        areas = []
    return render_template(
        'law.html',
        behaviors=behaviors,
        enforcers=enforcers,
        areas=areas
    )


@app.route('/law/add', methods=['POST'])
def law_add():
    db = get_db()
    dao = EnforcementDAO(db)
    try:
        # 获取当前时间用于 ID 生成
        now = datetime.datetime.now()
        date_str = now.strftime('%Y%m%d')  # 格式：20251216

        # 获取用户输入的 behavior_id 的后缀 (假设用户输入的是 IB-YYYYMMDD-XXXX)
        behavior_id = request.form.get('behavior_id')
        id_suffix = behavior_id.split('-')[-1] if '-' in behavior_id else '0001'

        ill_data = {
            'behavior_id': behavior_id,
            'behavior_type': request.form.get('behavior_type'),
            'occur_time': datetime.datetime.strptime(
                request.form.get('occur_time'), '%Y-%m-%dT%H:%M'
            ),
            'occur_area_id': request.form.get('occur_area_id'),
            'evidence_path': request.form.get('evidence_path'),
            'handle_status': '未处理',  # 之前修复的枚举值
            'enforcer_id': request.form.get('enforcer_id'),
            'penalty_basis': request.form.get('penalty_basis')
        }

        # 【修复点】生成符合 ED-YYYYMMDD-XXXX 格式的 dispatch_id
        # 将 DIS- 改为 ED-，并加上日期
        formatted_dispatch_id = f"ED-{date_str}-{id_suffix}"

        disp_data = {
            'dispatch_id': formatted_dispatch_id,
            'enforcer_id': request.form.get('enforcer_id'),
            'dispatch_time': now,
            'dispatch_status': '已派单'  # 注意：请确认数据字典枚举是 '已派单' 还是 '已派发'
        }

        # 再次检查数据字典 ，dispatch_status 枚举通常为：待响应 / 已派单 / 已完成
        # 如果您的数据库报错 dispatch_status，请尝试改为 '待响应' 或 '已派单'

        dao.create_dispatch(ill_data, disp_data)
        db.commit()
        flash(f'✅ 违法记录已上报，调度单号：{formatted_dispatch_id}', 'success')

    except Exception as e:
        db.rollback()
        flash(f'❌ 上报失败: {str(e)}', 'danger')
        app.logger.error(f'执法记录添加错误: {str(e)}')

    return redirect(url_for('law_list'))


@app.route('/research')
def research_list():
    db = get_db()
    try:
        projects = db.query(ResearchProject).options(
            joinedload(ResearchProject.leader)
        ).all()
        researchers = db.query(ResearcherInfo).all()
        app.logger.info(f"查询到科研项目: {len(projects)} 个")
    except Exception as e:
        flash(f'科研数据加载失败: {str(e)}', 'danger')
        projects = []
        researchers = []
    return render_template(
        'research.html',
        projects=projects,
        researchers=researchers
    )


@app.route('/research/add', methods=['POST'])
def research_add():
    db = get_db()
    dao = ResearchDAO(db)
    try:
        data = request.form.to_dict()
        data['project_start_date'] = datetime.datetime.strptime(data['project_start_date'], '%Y-%m-%d').date()
        data['project_end_date'] = datetime.datetime.strptime(data['project_end_date'], '%Y-%m-%d').date()
        dao.add_project(data)
        db.commit()
        flash('✅ 科研项目立项成功', 'success')
    except Exception as e:
        db.rollback()
        flash(f'❌ 立项失败: {str(e)}', 'danger')
        app.logger.error(f'科研项目添加错误: {str(e)}')
    return redirect(url_for('research_list'))


@app.route('/research/delete/<id>')
def research_delete(id):
    db = get_db()
    dao = ResearchDAO(db)
    try:
        if dao.delete_project(id):
            db.commit()
            flash('✅ 项目已删除', 'success')
        else:
            flash('❌ 未找到对应项目', 'danger')
    except Exception as e:
        db.rollback()
        flash(f'❌ 删除失败: {str(e)}', 'danger')
        app.logger.error(f'科研项目删除错误: {str(e)}')
    return redirect(url_for('research_list'))


# 错误处理页面
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')