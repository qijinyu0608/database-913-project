# 文件名: models.py
from sqlalchemy import Column, String, DateTime, Integer, Numeric, Text, ForeignKey, Date, Boolean, SmallInteger
from sqlalchemy.orm import relationship
from db_config import Base


# ==========================================
# 一、共享基础表 (跨业务线通用)
# ==========================================

class AreaInfo(Base):
    """区域信息表 tb_area_info"""
    __tablename__ = 'tb_area_info'
    __table_args__ = {'schema': 'dbo'}
    area_id = Column(String(20), primary_key=True, comment='区域编号')
    area_name = Column(String(50), nullable=False, comment='区域名称')
    area_level = Column(String(20), nullable=False, comment='区域级别')
    area_lng_range = Column(String(50), nullable=False, comment='区域经度范围')
    area_lat_range = Column(String(50), nullable=False, comment='区域纬度范围')

    monitors = relationship("MonitorDevice", back_populates="deploy_area")
    environments = relationship("EnvironmentData", back_populates="area_info")
    flow_control = relationship("FlowControl", uselist=False, back_populates="area_info")
    visitor_tracks = relationship("VisitorTrack", back_populates="located_area")
    illegal_behaviors = relationship("IllegalBehavior", back_populates="occur_area_info")
    video_monitors = relationship("VideoMonitor", back_populates="deploy_area")
    research_collects = relationship("ResearchDataCollect", back_populates="collect_area")


class StaffInfo(Base):
    """工作人员表 tb_staff_info"""
    __tablename__ = 'tb_staff_info'
    __table_args__ = {'schema': 'dbo'}
    staff_id = Column(String(20), primary_key=True, comment='工作人员编号')
    staff_name = Column(String(20), nullable=False, comment='工作人员姓名')
    staff_role = Column(String(20), nullable=False, comment='工作人员角色')
    department = Column(String(30), nullable=False, comment='所属部门')
    contact_phone = Column(String(11), nullable=False, comment='联系电话')

    # 【统一命名】主表的关联属性名为 auth
    auth = relationship("StaffAuth", uselist=False, back_populates="staff")
    law_enforcer = relationship("LawEnforcer", uselist=False, back_populates="staff_info")


class StaffAuth(Base):
    """员工认证信息表 tb_staff_auth"""
    __tablename__ = 'tb_staff_auth'
    __table_args__ = {'schema': 'dbo'}
    staff_id = Column(String(20), ForeignKey('dbo.tb_staff_info.staff_id'), primary_key=True, comment='员工编号')
    password_hash = Column(String(64), nullable=False, comment='密码哈希值')
    login_fail_count = Column(Integer, default=0, comment='登录失败次数')
    is_locked = Column(Integer, default=0, comment='账号锁定状态')
    last_login_time = Column(DateTime, comment='最后一次登录时间')

    # 反向关联指向 StaffInfo.auth
    staff = relationship("StaffInfo", back_populates="auth")


class LawEnforceDevice(Base):
    """执法设备表 tb_law_enforce_device"""
    __tablename__ = 'tb_law_enforce_device'
    __table_args__ = {'schema': 'dbo'}
    device_id = Column(String(20), primary_key=True, comment='执法设备编号')
    device_type = Column(String(30), nullable=False, comment='设备类型')
    device_status = Column(String(10), nullable=False, comment='设备状态')
    last_check_time = Column(Date, nullable=False, comment='上次校验时间')
    law_enforcer = relationship("LawEnforcer", uselist=False, back_populates="device_info")


class MonitorDevice(Base):
    """监测设备信息表 tb_monitor_device"""
    __tablename__ = 'tb_monitor_device'
    __table_args__ = {'schema': 'dbo'}
    device_id = Column(String(20), primary_key=True, comment='监测设备编号')
    device_type = Column(String(30), nullable=False, comment='设备类型')
    deploy_area_id = Column(String(20), ForeignKey('dbo.tb_area_info.area_id'), comment='部署区域编号')
    install_time = Column(Date, nullable=False, comment='安装时间')
    calibration_cycle = Column(Integer, nullable=False, comment='校准周期(天)')
    running_status = Column(String(10), nullable=False, comment='运行状态')
    communication_protocol = Column(String(20), nullable=False, comment='通信协议')
    deploy_area = relationship("AreaInfo", back_populates="monitors")


# ==========================================
# 二、生物多样性监测业务线
# ==========================================

class SpeciesInfo(Base):
    """物种信息表 tb_species_info"""
    __tablename__ = 'tb_species_info'
    __table_args__ = {'schema': 'dbo'}
    species_id = Column(String(20), primary_key=True, comment='物种编号')
    species_name_cn = Column(String(50), nullable=False, comment='物种中文名称')
    species_name_latin = Column(String(100), nullable=False, comment='物种拉丁名')
    species_category = Column(String(100), nullable=False, comment='物种分类')
    protection_level = Column(String(10), nullable=False, comment='保护级别')
    living_habit = Column(Text, comment='生存习性')
    distribution_range = Column(Text, comment='分布范围描述')
    monitor_records = relationship("MonitorRecord", back_populates="species_info")


class MonitorRecord(Base):
    """监测记录表 tb_monitor_record"""
    __tablename__ = 'tb_monitor_record'
    __table_args__ = {'schema': 'dbo'}
    record_id = Column(String(30), primary_key=True, comment='监测记录编号')
    species_id = Column(String(20), ForeignKey('dbo.tb_species_info.species_id'), comment='物种编号')
    device_id = Column(String(20), ForeignKey('dbo.tb_monitor_device.device_id'), comment='监测设备编号')
    monitor_time = Column(DateTime, nullable=False, comment='监测时间')
    monitor_lng = Column(Numeric(10, 6), nullable=False, comment='监测地点经度')
    monitor_lat = Column(Numeric(9, 6), nullable=False, comment='监测地点纬度')
    monitor_method = Column(String(20), nullable=False, comment='监测方式')
    monitor_content = Column(Text, nullable=False, comment='监测内容')
    recorder_id = Column(String(20), ForeignKey('dbo.tb_staff_info.staff_id'), comment='记录人编号')
    data_status = Column(String(10), nullable=False, comment='数据状态')
    species_info = relationship("SpeciesInfo", back_populates="monitor_records")
    device_info = relationship("MonitorDevice")
    recorder = relationship("StaffInfo", foreign_keys=[recorder_id])


class HabitatInfo(Base):
    """栖息地信息表 tb_habitat_info"""
    __tablename__ = 'tb_habitat_info'
    __table_args__ = {'schema': 'dbo'}
    habitat_id = Column(String(20), primary_key=True, comment='栖息地编号')
    area_name = Column(String(50), nullable=False, comment='区域名称')
    ecological_type = Column(String(20), nullable=False, comment='生态类型')
    area_size = Column(Numeric(10, 2), nullable=False, comment='栖息地面积')
    core_protection_range = Column(Text, nullable=False, comment='核心保护范围')
    main_species_id = Column(String(20), ForeignKey('dbo.tb_species_info.species_id'), comment='主要物种编号')
    environment_suitability = Column(Integer, nullable=False, comment='环境适宜性评分')


class HabitatSpeciesRel(Base):
    """物种 - 栖息地关联表 tb_habitat_species_rel"""
    __tablename__ = 'tb_habitat_species_rel'
    __table_args__ = {'schema': 'dbo'}
    rel_id = Column(String(30), primary_key=True, comment='关联记录编号')
    habitat_id = Column(String(20), ForeignKey('dbo.tb_habitat_info.habitat_id'), nullable=False, comment='栖息地编号')
    species_id = Column(String(20), ForeignKey('dbo.tb_species_info.species_id'), nullable=False, comment='物种编号')
    distribution_ratio = Column(Numeric(5, 2), nullable=False, comment='分布占比')
    habitat = relationship("HabitatInfo")
    species = relationship("SpeciesInfo")


# ==========================================
# 三、生态环境监测业务线
# ==========================================

class MonitorIndex(Base):
    """监测指标信息表 tb_monitor_index"""
    __tablename__ = 'tb_monitor_index'
    __table_args__ = {'schema': 'dbo'}
    index_id = Column(String(20), primary_key=True, comment='指标编号')
    index_name = Column(String(30), nullable=False, comment='指标名称')
    unit = Column(String(10), nullable=False, comment='计量单位')
    standard_upper = Column(Numeric(10, 2), comment='标准阈值上限')
    standard_lower = Column(Numeric(10, 2), comment='标准阈值下限')
    monitor_frequency = Column(String(10), nullable=False, comment='监测频率')


class EnvironmentData(Base):
    """环境监测数据表 tb_environment_data"""
    __tablename__ = 'tb_environment_data'
    __table_args__ = {'schema': 'dbo'}
    data_id = Column(String(30), primary_key=True, comment='环境数据编号')
    index_id = Column(String(20), ForeignKey('dbo.tb_monitor_index.index_id'), comment='指标编号')
    device_id = Column(String(20), ForeignKey('dbo.tb_monitor_device.device_id'), comment='监测设备编号')
    collect_time = Column(DateTime, nullable=False, comment='采集时间')
    monitor_value = Column(Numeric(10, 2), nullable=False, comment='监测值')
    area_id = Column(String(20), ForeignKey('dbo.tb_area_info.area_id'), comment='区域编号')
    data_quality = Column(String(10), nullable=False, comment='数据质量')
    index_info = relationship("MonitorIndex")
    device_info = relationship("MonitorDevice")
    area_info = relationship("AreaInfo", back_populates="environments")


# ==========================================
# 四、游客智能管理业务线
# ==========================================

class VisitorInfo(Base):
    """游客信息表 tb_visitor_info"""
    __tablename__ = 'tb_visitor_info'
    __table_args__ = {'schema': 'dbo'}
    visitor_id = Column(String(20), primary_key=True, comment='游客编号')
    visitor_name = Column(String(20), nullable=False, comment='游客姓名')
    id_card = Column(String(18), unique=True, nullable=False, comment='身份证号')
    contact_phone = Column(String(11), nullable=False, comment='联系电话')
    check_in_time = Column(DateTime, comment='入园时间')
    check_out_time = Column(DateTime, comment='离园时间')
    check_in_method = Column(String(20), nullable=False, comment='入园方式')

    # 【统一命名】auth (对应 app.py 中的检查逻辑)
    auth = relationship("VisitorAuth", uselist=False, back_populates="visitor_info")
    reservation = relationship("ReservationRecord", uselist=False, back_populates="visitor")


class VisitorAuth(Base):
    """游客认证表 tb_visitor_auth"""
    __tablename__ = 'tb_visitor_auth'
    __table_args__ = {'schema': 'dbo'}
    visitor_id = Column(String(30), ForeignKey('dbo.tb_visitor_info.visitor_id'), primary_key=True, comment='游客ID')
    password_hash = Column(String(64), nullable=False, comment='密码哈希值')
    login_fail_count = Column(Integer, default=0, comment='登录失败次数')
    is_locked = Column(Integer, default=0, comment='是否锁定')
    last_login_time = Column(DateTime, comment='最后登录时间')

    # 【已注释】数据库无此字段，注释以修复报错
    # account_status = Column(String(10), default='正常', comment='账号状态')

    # 反向关联指向 VisitorInfo.auth
    visitor_info = relationship("VisitorInfo", back_populates="auth")


class ReservationRecord(Base):
    """预约记录表 tb_reservation_record"""
    __tablename__ = 'tb_reservation_record'
    __table_args__ = {'schema': 'dbo'}
    reservation_id = Column(String(30), primary_key=True, comment='预约记录编号')
    visitor_id = Column(String(20), ForeignKey('dbo.tb_visitor_info.visitor_id'), comment='游客编号', unique=True)
    reservation_date = Column(Date, nullable=False, comment='预约日期')
    check_in_period = Column(String(20), nullable=False, comment='入园时段')
    companion_count = Column(Integer, nullable=False, comment='同行人数')
    reservation_status = Column(String(10), nullable=False, comment='预约状态')
    ticket_amount = Column(Numeric(10, 2), nullable=False, comment='购票金额')
    payment_status = Column(String(10), nullable=False, comment='支付状态')
    visitor = relationship("VisitorInfo", back_populates="reservation")


class VisitorTrack(Base):
    """游客轨迹数据表 tb_visitor_track"""
    __tablename__ = 'tb_visitor_track'
    __table_args__ = {'schema': 'dbo'}
    track_id = Column(String(30), primary_key=True, comment='轨迹记录编号')
    visitor_id = Column(String(20), ForeignKey('dbo.tb_visitor_info.visitor_id'), comment='游客编号')
    locate_time = Column(DateTime, nullable=False, comment='定位时间')
    real_time_lng = Column(Numeric(10, 6), nullable=False, comment='实时经度')
    real_time_lat = Column(Numeric(9, 6), nullable=False, comment='实时纬度')
    located_area_id = Column(String(20), ForeignKey('dbo.tb_area_info.area_id'), comment='所在区域编号')
    is_out_of_route = Column(SmallInteger, nullable=False, comment='是否超出规定路线')
    visitor_info = relationship("VisitorInfo")
    located_area = relationship("AreaInfo", back_populates="visitor_tracks")


class FlowControl(Base):
    """流量控制信息表 tb_flow_control"""
    __tablename__ = 'tb_flow_control'
    __table_args__ = {'schema': 'dbo'}
    area_id = Column(String(20), ForeignKey('dbo.tb_area_info.area_id'), primary_key=True, comment='区域编号')
    daily_max_capacity = Column(Integer, nullable=False, comment='日最大承载量')
    real_time_visitor_count = Column(Integer, nullable=False, comment='实时在园人数')
    warning_threshold = Column(Integer, nullable=False, comment='预警阈值')
    current_status = Column(String(10), nullable=False, comment='当前状态')
    area_info = relationship("AreaInfo", back_populates="flow_control")


# ==========================================
# 五、执法监管业务线
# ==========================================

class LawEnforcer(Base):
    """执法人员信息表 tb_law_enforcer"""
    __tablename__ = 'tb_law_enforcer'
    __table_args__ = {'schema': 'dbo'}
    enforcer_id = Column(String(20), ForeignKey('dbo.tb_staff_info.staff_id'), primary_key=True, comment='执法人员编号')
    enforcer_name = Column(String(20), nullable=False, comment='执法人员姓名')
    department = Column(String(30), nullable=False, comment='所属部门')
    enforcement_permission = Column(String(50), nullable=False, comment='执法权限')
    contact_phone = Column(String(11), nullable=False, comment='联系电话')
    law_enforce_device_id = Column(String(20), ForeignKey('dbo.tb_law_enforce_device.device_id'),
                                   comment='执法设备编号')

    device_info = relationship("LawEnforceDevice", back_populates="law_enforcer")
    staff_info = relationship("StaffInfo", back_populates="law_enforcer", foreign_keys=[enforcer_id])

    # 【统一命名】auth (之前是 auth_info)
    auth = relationship("EnforcerAuth", uselist=False, back_populates="enforcer_info")


class EnforcerAuth(Base):
    """执法人员认证表 tb_enforcer_auth"""
    __tablename__ = 'tb_enforcer_auth'
    __table_args__ = {'schema': 'dbo'}
    enforcer_id = Column(String(30), ForeignKey('dbo.tb_law_enforcer.enforcer_id'), primary_key=True,
                         comment='执法人员ID')
    password_hash = Column(String(64), nullable=False, comment='密码哈希值')
    login_fail_count = Column(Integer, default=0, comment='登录失败次数')
    is_locked = Column(Integer, default=0, comment='是否锁定')
    last_login_time = Column(DateTime, comment='最后登录时间')

    # 【已注释】数据库无此字段
    # permission_level = Column(String(20), default='基础', comment='权限等级')

    # 反向关联指向 LawEnforcer.auth
    enforcer_info = relationship("LawEnforcer", back_populates="auth")


class IllegalBehavior(Base):
    """非法行为记录表 tb_illegal_behavior"""
    __tablename__ = 'tb_illegal_behavior'
    __table_args__ = {'schema': 'dbo'}
    behavior_id = Column(String(30), primary_key=True, comment='非法行为记录编号')
    behavior_type = Column(String(30), nullable=False, comment='行为类型')
    occur_time = Column(DateTime, nullable=False, comment='发生时间')
    occur_area_id = Column(String(20), ForeignKey('dbo.tb_area_info.area_id'), comment='发生区域编号')
    evidence_path = Column(Text, nullable=False, comment='影像证据路径')
    handle_status = Column(String(10), nullable=False, comment='处理状态')
    enforcer_id = Column(String(20), ForeignKey('dbo.tb_law_enforcer.enforcer_id'), comment='执法人员编号')
    handle_result = Column(Text, comment='处理结果')
    penalty_basis = Column(String(100), nullable=False, comment='处罚依据')
    occur_area_info = relationship("AreaInfo", back_populates="illegal_behaviors")
    handling_enforcer = relationship("LawEnforcer", foreign_keys=[enforcer_id])


class EnforcementDispatch(Base):
    """执法调度信息表 tb_enforcement_dispatch"""
    __tablename__ = 'tb_enforcement_dispatch'
    __table_args__ = {'schema': 'dbo'}
    dispatch_id = Column(String(30), primary_key=True, comment='调度记录编号')
    behavior_id = Column(String(30), ForeignKey('dbo.tb_illegal_behavior.behavior_id'), comment='非法行为记录编号',
                         unique=True)
    enforcer_id = Column(String(20), ForeignKey('dbo.tb_law_enforcer.enforcer_id'), comment='执法人员编号')
    dispatch_time = Column(DateTime, nullable=False, comment='调度时间')
    response_time = Column(DateTime, comment='响应时间')
    handle_complete_time = Column(DateTime, comment='处置完成时间')
    dispatch_status = Column(String(10), nullable=False, comment='调度状态')


class VideoMonitor(Base):
    """视频监控点信息表 tb_video_monitor"""
    __tablename__ = 'tb_video_monitor'
    __table_args__ = {'schema': 'dbo'}
    monitor_point_id = Column(String(20), primary_key=True, comment='监控点编号')
    deploy_area_id = Column(String(20), ForeignKey('dbo.tb_area_info.area_id'), comment='部署区域编号')
    install_lng = Column(Numeric(10, 6), nullable=False, comment='安装位置经度')
    install_lat = Column(Numeric(9, 6), nullable=False, comment='安装位置纬度')
    monitor_range = Column(String(50), nullable=False, comment='监控范围')
    device_status = Column(String(10), nullable=False, comment='设备状态')
    data_storage_cycle = Column(Integer, nullable=False, comment='数据存储周期(天)')
    deploy_area = relationship("AreaInfo", back_populates="video_monitors")


# ==========================================
# 六、科研数据支撑业务线
# ==========================================

class ResearchProject(Base):
    """科研项目信息表 tb_research_project"""
    __tablename__ = 'tb_research_project'
    __table_args__ = {'schema': 'dbo'}
    project_id = Column(String(20), primary_key=True, comment='项目编号')
    project_name = Column(String(100), nullable=False, comment='项目名称')
    leader_id = Column(String(20), ForeignKey('dbo.tb_researcher_info.researcher_id'), comment='负责人编号')
    application_unit = Column(String(50), nullable=False, comment='申请单位')
    project_start_date = Column(Date, nullable=False, comment='立项时间')
    project_end_date = Column(Date, nullable=False, comment='结题时间')
    project_status = Column(String(10), nullable=False, comment='项目状态')
    research_field = Column(String(30), nullable=False, comment='研究领域')
    leader = relationship("ResearcherInfo")


class ResearchDataCollect(Base):
    """科研数据采集记录表 tb_research_data_collect"""
    __tablename__ = 'tb_research_data_collect'
    __table_args__ = {'schema': 'dbo'}
    collect_id = Column(String(30), primary_key=True, comment='采集记录编号')
    project_id = Column(String(20), ForeignKey('dbo.tb_research_project.project_id'), comment='项目编号')
    collector_id = Column(String(20), ForeignKey('dbo.tb_researcher_info.researcher_id'), comment='采集人编号')
    collect_time = Column(DateTime, nullable=False, comment='采集时间')
    collect_area_id = Column(String(20), ForeignKey('dbo.tb_area_info.area_id'), comment='采集区域编号')
    collect_content = Column(Text, nullable=False, comment='采集内容')
    data_source = Column(String(20), nullable=False, comment='数据来源')
    project = relationship("ResearchProject")
    collector = relationship("ResearcherInfo", foreign_keys=[collector_id])
    collect_area = relationship("AreaInfo", back_populates="research_collects")


class ResearchAchievement(Base):
    """科研成果信息表 tb_research_achievement"""
    __tablename__ = 'tb_research_achievement'
    __table_args__ = {'schema': 'dbo'}
    achievement_id = Column(String(20), primary_key=True, comment='成果编号')
    project_id = Column(String(20), ForeignKey('dbo.tb_research_project.project_id'), comment='项目编号')
    achievement_type = Column(String(20), nullable=False, comment='成果类型')
    achievement_name = Column(String(100), nullable=False, comment='成果名称')
    publish_submit_time = Column(Date, nullable=False, comment='发表/提交时间')
    share_permission = Column(String(10), nullable=False, comment='共享权限')
    file_path = Column(Text, nullable=False, comment='文件路径')
    project = relationship("ResearchProject", foreign_keys=[project_id])


class ResearcherInfo(Base):
    """科研人员表 tb_researcher_info"""
    __tablename__ = 'tb_researcher_info'
    __table_args__ = {'schema': 'dbo'}
    researcher_id = Column(String(20), primary_key=True, comment='科研人员编号')
    researcher_name = Column(String(20), nullable=False, comment='科研人员姓名')
    affiliated_unit = Column(String(50), nullable=False, comment='所属单位')
    research_field = Column(String(30), nullable=False, comment='研究领域')
    contact_info = Column(String(50), nullable=False, comment='联系方式')

    # 【统一命名】auth (之前是 auth_info)
    auth = relationship("ResearcherAuth", uselist=False, back_populates="researcher_info")


class ResearcherAuth(Base):
    """科研人员认证表 tb_researcher_auth"""
    __tablename__ = 'tb_researcher_auth'
    __table_args__ = {'schema': 'dbo'}
    researcher_id = Column(String(30), ForeignKey('dbo.tb_researcher_info.researcher_id'), primary_key=True,
                           comment='科研人员ID')
    password_hash = Column(String(64), nullable=False, comment='密码哈希值')
    login_fail_count = Column(Integer, default=0, comment='登录失败次数')
    is_locked = Column(Integer, default=0, comment='是否锁定')
    last_login_time = Column(DateTime, comment='最后登录时间')

    # 【已注释】数据库无此字段
    # data_access_level = Column(String(20), default='普通', comment='数据访问等级')

    # 反向关联指向 ResearcherInfo.auth
    researcher_info = relationship("ResearcherInfo", back_populates="auth")
