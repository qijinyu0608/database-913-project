from sqlalchemy import Column, String, DateTime, Integer, Numeric, Text, ForeignKey, Date, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
from db_config import Base


# ==========================================
# 一、共享基础表 (跨业务线通用) [cite: 180]
# ==========================================

class AreaInfo(Base):
    """区域信息表 tb_area_info"""
    __tablename__ = 'tb_area_info'
    area_id = Column(String(20), primary_key=True)  # AREA-2025-xxxx
    area_name = Column(String(50), nullable=False)
    area_level = Column(String(20), nullable=False)  # 核心保护区/缓冲区/实验区
    area_lng_range = Column(String(50), nullable=False)
    area_lat_range = Column(String(50), nullable=False)


class StaffInfo(Base):
    """工作人员表 tb_staff_info"""
    __tablename__ = 'tb_staff_info'
    staff_id = Column(String(20), primary_key=True)  # STAFF-2025-xxxx
    staff_name = Column(String(20), nullable=False)
    staff_role = Column(String(20), nullable=False)
    department = Column(String(30), nullable=False)
    contact_phone = Column(String(11), nullable=False)

    # 关联认证表 (一对一)
    auth = relationship("StaffAuth", uselist=False, back_populates="staff")


class MonitorDevice(Base):
    """监测设备表 tb_monitor_device"""
    __tablename__ = 'tb_monitor_device'
    device_id = Column(String(20), primary_key=True)  # MD-2025-xxxx
    device_type = Column(String(30), nullable=False)
    deploy_area_id = Column(String(20), ForeignKey('tb_area_info.area_id'))
    install_time = Column(Date, nullable=False)
    calibration_cycle = Column(Integer, nullable=False)
    running_status = Column(String(10), nullable=False)  # 正常/故障/离线
    communication_protocol = Column(String(20), nullable=False)


# 安全认证表 (系统辅助表)
class StaffAuth(Base):
    __tablename__ = 'tb_staff_auth'
    staff_id = Column(String(20), ForeignKey('tb_staff_info.staff_id'), primary_key=True)
    password_hash = Column(String(64), nullable=False)
    login_fail_count = Column(Integer, default=0)
    is_locked = Column(Integer, default=0)
    last_login_time = Column(DateTime)
    staff = relationship("StaffInfo", back_populates="auth")


# ==========================================
# 二、生物多样性监测业务线 [cite: 197]
# ==========================================

class SpeciesInfo(Base):
    __tablename__ = 'tb_species_info'
    species_id = Column(String(20), primary_key=True)  # SP-2025-xxxx
    species_name_cn = Column(String(50), nullable=False)
    species_name_latin = Column(String(100), nullable=False)
    species_category = Column(String(100), nullable=False)
    protection_level = Column(String(10), nullable=False)
    living_habit = Column(Text)
    distribution_range = Column(Text)


class HabitatInfo(Base):
    __tablename__ = 'tb_habitat_info'
    habitat_id = Column(String(20), primary_key=True)  # HT-2025-xxxx
    area_name = Column(String(50), nullable=False)
    ecological_type = Column(String(20), nullable=False)
    area_size = Column(Numeric(10, 2), nullable=False)
    core_protection_range = Column(Text, nullable=False)
    main_species_id = Column(String(20), ForeignKey('tb_species_info.species_id'))
    environment_suitability = Column(Integer, nullable=False)  # 1-100


class MonitorRecord(Base):
    __tablename__ = 'tb_monitor_record'
    record_id = Column(String(30), primary_key=True)  # MR-2025xxxx
    species_id = Column(String(20), ForeignKey('tb_species_info.species_id'))
    device_id = Column(String(20), ForeignKey('tb_monitor_device.device_id'))
    monitor_time = Column(DateTime, nullable=False)
    monitor_lng = Column(Numeric(10, 6), nullable=False)
    monitor_lat = Column(Numeric(9, 6), nullable=False)
    monitor_method = Column(String(20), nullable=False)
    monitor_content = Column(Text, nullable=False)
    recorder_id = Column(String(20), ForeignKey('tb_staff_info.staff_id'))
    data_status = Column(String(10), nullable=False)


# ==========================================
# 三、生态环境监测业务线 [cite: 214]
# ==========================================

class MonitorIndex(Base):
    __tablename__ = 'tb_monitor_index'
    index_id = Column(String(20), primary_key=True)  # MI-2025-xxxx
    index_name = Column(String(30), nullable=False)
    unit = Column(String(10), nullable=False)
    standard_upper = Column(Numeric(10, 2))
    standard_lower = Column(Numeric(10, 2))
    monitor_frequency = Column(String(10), nullable=False)


class EnvironmentData(Base):
    __tablename__ = 'tb_environment_data'
    data_id = Column(String(30), primary_key=True)  # ED-2025xxxx
    index_id = Column(String(20), ForeignKey('tb_monitor_index.index_id'))
    device_id = Column(String(20), ForeignKey('tb_monitor_device.device_id'))
    collect_time = Column(DateTime, nullable=False)
    monitor_value = Column(Numeric(10, 2), nullable=False)
    area_id = Column(String(20), ForeignKey('tb_area_info.area_id'))
    data_quality = Column(String(10), nullable=False)

    index_info = relationship("MonitorIndex")  # 便于关联查询阈值


# ==========================================
# 四、游客智能管理业务线 [cite: 227]
# ==========================================

class VisitorInfo(Base):
    __tablename__ = 'tb_visitor_info'
    visitor_id = Column(String(20), primary_key=True)  # VI-2025-xxxx
    visitor_name = Column(String(20), nullable=False)
    id_card = Column(String(18), unique=True, nullable=False)
    contact_phone = Column(String(11), nullable=False)
    check_in_time = Column(DateTime)
    check_out_time = Column(DateTime)
    check_in_method = Column(String(20), nullable=False)


class ReservationRecord(Base):
    __tablename__ = 'tb_reservation_record'
    reservation_id = Column(String(30), primary_key=True)  # RR-2025xxxx
    visitor_id = Column(String(20), ForeignKey('tb_visitor_info.visitor_id'))
    reservation_date = Column(Date, nullable=False)
    check_in_period = Column(String(20), nullable=False)
    companion_count = Column(Integer, nullable=False)
    reservation_status = Column(String(10), nullable=False)
    ticket_amount = Column(Numeric(10, 2), nullable=False)
    payment_status = Column(String(10), nullable=False)


class VisitorTrack(Base):
    __tablename__ = 'tb_visitor_track'
    track_id = Column(String(30), primary_key=True)
    visitor_id = Column(String(20), ForeignKey('tb_visitor_info.visitor_id'))
    locate_time = Column(DateTime, nullable=False)
    real_time_lng = Column(Numeric(10, 6), nullable=False)
    real_time_lat = Column(Numeric(9, 6), nullable=False)
    located_area_id = Column(String(20), ForeignKey('tb_area_info.area_id'))
    is_out_of_route = Column(Integer, nullable=False)  # 0/1


class FlowControl(Base):
    __tablename__ = 'tb_flow_control'
    area_id = Column(String(20), ForeignKey('tb_area_info.area_id'), primary_key=True)
    daily_max_capacity = Column(Integer, nullable=False)
    real_time_visitor_count = Column(Integer, nullable=False)
    warning_threshold = Column(Integer, nullable=False)
    current_status = Column(String(10), nullable=False)  # 正常/预警/限流


# ==========================================
# 五、执法监管业务线 [cite: 244]
# ==========================================

class LawEnforcer(Base):
    __tablename__ = 'tb_law_enforcer'
    enforcer_id = Column(String(20), primary_key=True)  # LE-2025-xxxx
    enforcer_name = Column(String(20), nullable=False)
    department = Column(String(30), nullable=False)
    enforcement_permission = Column(String(50), nullable=False)
    contact_phone = Column(String(11), nullable=False)
    law_enforce_device_id = Column(String(20), ForeignKey('tb_law_enforce_device.device_id'))


class LawEnforceDevice(Base):
    __tablename__ = 'tb_law_enforce_device'
    device_id = Column(String(20), primary_key=True)
    device_type = Column(String(30), nullable=False)
    device_status = Column(String(10), nullable=False)
    last_check_time = Column(Date, nullable=False)


class IllegalBehavior(Base):
    __tablename__ = 'tb_illegal_behavior'
    behavior_id = Column(String(30), primary_key=True)  # IB-2025xxxx
    behavior_type = Column(String(30), nullable=False)
    occur_time = Column(DateTime, nullable=False)
    occur_area_id = Column(String(20), ForeignKey('tb_area_info.area_id'))
    evidence_path = Column(Text, nullable=False)
    handle_status = Column(String(10), nullable=False)
    enforcer_id = Column(String(20), ForeignKey('tb_law_enforcer.enforcer_id'))
    handle_result = Column(Text)
    penalty_basis = Column(String(100), nullable=False)


class EnforcementDispatch(Base):
    __tablename__ = 'tb_enforcement_dispatch'
    dispatch_id = Column(String(30), primary_key=True)
    behavior_id = Column(String(30), ForeignKey('tb_illegal_behavior.behavior_id'))
    enforcer_id = Column(String(20), ForeignKey('tb_law_enforcer.enforcer_id'))
    dispatch_time = Column(DateTime, nullable=False)
    response_time = Column(DateTime)
    handle_complete_time = Column(DateTime)
    dispatch_status = Column(String(10), nullable=False)


# ==========================================
# 六、科研数据支撑业务线 [cite: 261]
# ==========================================

class ResearcherInfo(Base):
    __tablename__ = 'tb_researcher_info'
    researcher_id = Column(String(20), primary_key=True)  # RE-2025-xxxx
    researcher_name = Column(String(20), nullable=False)
    affiliated_unit = Column(String(50), nullable=False)
    research_field = Column(String(30), nullable=False)
    contact_info = Column(String(50), nullable=False)


class ResearchProject(Base):
    __tablename__ = 'tb_research_project'
    project_id = Column(String(20), primary_key=True)  # RP-2025-xxxx
    project_name = Column(String(100), nullable=False)
    leader_id = Column(String(20), ForeignKey('tb_researcher_info.researcher_id'))
    application_unit = Column(String(50), nullable=False)
    project_start_date = Column(Date, nullable=False)
    project_end_date = Column(Date, nullable=False)
    project_status = Column(String(10), nullable=False)
    research_field = Column(String(30), nullable=False)


class ResearchDataCollect(Base):
    __tablename__ = 'tb_research_data_collect'
    collect_id = Column(String(30), primary_key=True)
    project_id = Column(String(20), ForeignKey('tb_research_project.project_id'))
    collector_id = Column(String(20), ForeignKey('tb_researcher_info.researcher_id'))
    collect_time = Column(DateTime, nullable=False)
    collect_area_id = Column(String(20), ForeignKey('tb_area_info.area_id'))
    collect_content = Column(Text, nullable=False)
    data_source = Column(String(20), nullable=False)


class ResearchAchievement(Base):
    """科研成果表 tb_research_achievement"""
    __tablename__ = 'tb_research_achievement'

    achievement_id = Column(String(20), primary_key=True)  # RA-2025-xxxx
    project_id = Column(String(20), ForeignKey('tb_research_project.project_id'))
    achievement_type = Column(String(20), nullable=False)
    achievement_name = Column(String(100), nullable=False)
    publish_submit_time = Column(Date, nullable=False)
    share_permission = Column(String(10), nullable=False)
    file_path = Column(Text, nullable=False)