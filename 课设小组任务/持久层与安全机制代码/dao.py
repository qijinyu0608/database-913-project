from sqlalchemy.orm import Session
from sqlalchemy import func
from models import *
import datetime


class BioDiversityDAO:
    """1. 生物多样性监测 DAO"""

    def __init__(self, db: Session):
        self.db = db

    def add_monitor_record(self, record_data: dict):
        """新增监测记录 (事务)"""
        try:
            new_record = MonitorRecord(**record_data)
            self.db.add(new_record)
            self.db.commit()
            return new_record
        except Exception as e:
            self.db.rollback()
            raise e

    def get_species_by_category(self, category_keyword: str):
        """查询检索：根据分类模糊查询"""
        return self.db.query(SpeciesInfo).filter(
            SpeciesInfo.species_category.like(f"%{category_keyword}%")
        ).all()


class EnvironmentDAO:
    """2. 生态环境监测 DAO"""

    def __init__(self, db: Session):
        self.db = db

    def add_environment_data(self, data_dict: dict):
        """
        新增环境数据，并自动检查是否异常 (根据指标阈值)
        """
        try:
            # 1. 获取指标阈值
            index = self.db.get(MonitorIndex, data_dict['index_id'])
            if not index:
                raise ValueError("指标不存在")

            # 2. 判断数据质量/异常逻辑 (简化版)
            val = float(data_dict['monitor_value'])
            quality = '优'
            if index.standard_upper and val > float(index.standard_upper):
                quality = '差'  # 超标

            data_dict['data_quality'] = quality

            # 3. 插入数据
            new_data = EnvironmentData(**data_dict)
            self.db.add(new_data)
            self.db.commit()
            return new_data
        except Exception as e:
            self.db.rollback()
            raise e


class VisitorDAO:
    """3. 游客智能管理 DAO"""

    def __init__(self, db: Session):
        self.db = db

    def make_reservation(self, visitor_dict: dict, reservation_dict: dict):
        """
        提交预约 (事务：涉及游客信息表和预约记录表)
        """
        try:
            # 1. 检查或创建游客
            visitor = self.db.query(VisitorInfo).filter_by(id_card=visitor_dict['id_card']).first()
            if not visitor:
                visitor = VisitorInfo(**visitor_dict)
                self.db.add(visitor)
                self.db.flush()  # 获取 ID 但不提交

            # 2. 创建预约
            reservation = ReservationRecord(**reservation_dict)
            # 确保外键关联
            reservation.visitor_id = visitor.visitor_id
            self.db.add(reservation)

            self.db.commit()
            return reservation.reservation_id
        except Exception as e:
            self.db.rollback()
            raise e

    def update_flow_control(self, area_id: str, change_count: int):
        """更新区域实时人数，并检查是否触发熔断/限流"""
        try:
            flow = self.db.get(FlowControl, area_id)
            if flow:
                flow.real_time_visitor_count += change_count
                # 触发状态变更逻辑 [cite: 44]
                if flow.real_time_visitor_count >= flow.warning_threshold:
                    flow.current_status = '预警'
                elif flow.real_time_visitor_count >= flow.daily_max_capacity:
                    flow.current_status = '限流'
                else:
                    flow.current_status = '正常'
                self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e


class EnforcementDAO:
    """4. 执法监管 DAO"""

    def __init__(self, db: Session):
        self.db = db

    def create_dispatch(self, illegal_dict: dict, dispatch_dict: dict):
        """
        生成非法行为记录并触发执法调度
        """
        try:
            # 1. 记录非法行为
            behavior = IllegalBehavior(**illegal_dict)
            self.db.add(behavior)
            self.db.flush()

            # 2. 生成调度单
            dispatch = EnforcementDispatch(**dispatch_dict)
            dispatch.behavior_id = behavior.behavior_id
            self.db.add(dispatch)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e


class ResearchDAO:
    """5. 科研数据支撑 DAO"""

    def __init__(self, db: Session):
        self.db = db

    def add_project(self, project_data: dict):
        """立项申请"""
        try:
            proj = ResearchProject(**project_data)
            self.db.add(proj)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e