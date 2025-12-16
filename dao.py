# 文件名: dao.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import *  # 导入所有模型
import datetime
from db_config import engine, Base


def create_all_tables():
    """根据models.py中的所有Base子类，创建所有表格结构"""
    print("正在根据 ORM 模型创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 所有表格创建完成。")


class BioDiversityDAO:
    """1. 生物多样性监测 DAO (完整 CRUD)"""

    def __init__(self, db: Session):
        self.db = db

    # --- Create (增) ---
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

    # --- Read (查) ---
    def get_record_by_id(self, record_id: str):
        """根据ID查询监测记录"""
        return self.db.get(MonitorRecord, record_id)

    def get_species_by_category(self, category_keyword: str):
        """模糊查询物种"""
        return self.db.query(SpeciesInfo).filter(
            SpeciesInfo.species_category.like(f"%{category_keyword}%")
        ).all()

    # --- Update (改) ---
    def update_record_content(self, record_id: str, new_content: str, new_status: str = None):
        """更新监测内容或状态"""
        record = self.db.get(MonitorRecord, record_id)
        if record:
            record.monitor_content = new_content
            if new_status:
                record.data_status = new_status
            self.db.commit()
            return record
        return None

    # --- Delete (删) ---
    def delete_record(self, record_id: str):
        """删除监测记录"""
        record = self.db.get(MonitorRecord, record_id)
        if record:
            self.db.delete(record)
            self.db.commit()
            return True
        return False


class EnvironmentDAO:
    """2. 生态环境监测 DAO (完整 CRUD)"""

    def __init__(self, db: Session):
        self.db = db

    # --- Create (增) ---
    def add_environment_data(self, data_dict: dict):
        """新增环境数据，自动判断指标阈值"""
        try:
            index = self.db.get(MonitorIndex, data_dict['index_id'])
            if not index:
                raise ValueError("指标不存在")

            val = float(data_dict['monitor_value'])
            quality = '优'
            # 逻辑判断：如果设置了上限且超过，则标记为 '差'
            if index.standard_upper and val > float(index.standard_upper):
                quality = '差'
                # 逻辑判断：如果设置了下限且低于，则标记为 '差'
            elif index.standard_lower and val < float(index.standard_lower):
                quality = '差'

            data_dict['data_quality'] = quality
            new_data = EnvironmentData(**data_dict)
            self.db.add(new_data)
            self.db.commit()
            return new_data
        except Exception as e:
            self.db.rollback()
            raise e

    # --- Read (查) ---
    def get_data_by_id(self, data_id: str):
        return self.db.get(EnvironmentData, data_id)

    # --- Update (改) ---
    def update_data_value(self, data_id: str, new_value: float):
        """修正环境监测数值 (例如设备校准后修正)"""
        data = self.db.get(EnvironmentData, data_id)
        if data:
            data.monitor_value = new_value
            # 重新触发质量判断逻辑
            index = self.db.get(MonitorIndex, data.index_id)
            if index:
                if (index.standard_upper and new_value > float(index.standard_upper)) or \
                        (index.standard_lower and new_value < float(index.standard_lower)):
                    data.data_quality = '差'
                else:
                    data.data_quality = '优'

            self.db.commit()
            return data
        return None

    # --- Delete (删) ---
    def delete_data(self, data_id: str):
        data = self.db.get(EnvironmentData, data_id)
        if data:
            self.db.delete(data)
            self.db.commit()
            return True
        return False


class VisitorDAO:
    """3. 游客智能管理 DAO (完整 CRUD)"""

    def __init__(self, db: Session):
        self.db = db

    # --- Create (增) ---
    def make_reservation(self, visitor_dict: dict, reservation_dict: dict):
        """提交预约 (事务：涉及游客 + 预约单)"""
        try:
            # 1. 检查或创建游客
            visitor = self.db.query(VisitorInfo).filter_by(id_card=visitor_dict['id_card']).first()
            if not visitor:
                visitor = VisitorInfo(**visitor_dict)
                self.db.add(visitor)
                self.db.flush()  # 确保拿到 visitor_id

            # 2. 创建预约
            reservation = ReservationRecord(**reservation_dict)
            reservation.visitor_id = visitor.visitor_id
            self.db.add(reservation)
            self.db.commit()
            return reservation.reservation_id
        except Exception as e:
            self.db.rollback()
            raise e

    # --- Read (查) ---
    def get_reservation(self, reservation_id: str):
        return self.db.get(ReservationRecord, reservation_id)

    # --- Update (改) ---
    def update_flow_control(self, area_id: str, change_count: int):
        """业务逻辑更新：流量控制与熔断"""
        try:
            flow = self.db.get(FlowControl, area_id)
            if flow:
                flow.real_time_visitor_count += change_count

                # 修复逻辑优先级：先判断最严重的“限流”，再判断“预警”
                if flow.real_time_visitor_count >= flow.daily_max_capacity:
                    flow.current_status = '限流'
                elif flow.real_time_visitor_count >= flow.warning_threshold:
                    flow.current_status = '预警'
                else:
                    flow.current_status = '正常'

                self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def cancel_reservation(self, reservation_id: str):
        """取消预约 (逻辑更新状态)"""
        res = self.db.get(ReservationRecord, reservation_id)
        if res:
            res.reservation_status = "已取消"
            self.db.commit()
            return True
        return False

    # --- Delete (删) ---
    def delete_reservation_physically(self, reservation_id: str):
        """物理删除预约单 (仅用于管理后台)"""
        res = self.db.get(ReservationRecord, reservation_id)
        if res:
            self.db.delete(res)
            self.db.commit()
            return True
        return False


class EnforcementDAO:
    """4. 执法监管 DAO (完整 CRUD)"""

    def __init__(self, db: Session):
        self.db = db

    # --- Create (增) ---
    def create_dispatch(self, illegal_dict: dict, dispatch_dict: dict):
        """生成非法行为记录并触发调度"""
        try:
            # 1. 记录非法行为
            behavior = IllegalBehavior(**illegal_dict)
            self.db.add(behavior)
            self.db.flush()  # 确保拿到 behavior_id

            # 2. 生成调度单
            dispatch = EnforcementDispatch(**dispatch_dict)
            dispatch.behavior_id = behavior.behavior_id
            self.db.add(dispatch)
            self.db.commit()
            return behavior.behavior_id
        except Exception as e:
            self.db.rollback()
            raise e

    # --- Read (查) ---
    def get_behavior_detail(self, behavior_id: str):
        return self.db.get(IllegalBehavior, behavior_id)

    # --- Update (改) ---
    def close_case(self, behavior_id: str, result_text: str):
        """结案处理"""
        behavior = self.db.get(IllegalBehavior, behavior_id)
        if behavior:
            behavior.handle_status = "已结案"  # 使用数据字典中的枚举值
            behavior.handle_result = result_text
            self.db.commit()
            return True
        return False

    # --- Delete (删) ---
    def delete_case_record(self, behavior_id: str):
        """删除案件记录 (级联删除调度单)"""
        try:
            # 1. 先删除关联的调度单（子表）
            dispatches = self.db.query(EnforcementDispatch).filter_by(behavior_id=behavior_id).all()
            for d in dispatches:
                self.db.delete(d)

            # 2. 再删除主表记录
            behavior = self.db.get(IllegalBehavior, behavior_id)
            if behavior:
                self.db.delete(behavior)
                self.db.commit()
                return True
        except Exception as e:
            self.db.rollback()
            raise e
        return False


class ResearchDAO:
    """5. 科研数据支撑 DAO (完整 CRUD)"""

    def __init__(self, db: Session):
        self.db = db

    # --- Create (增) ---
    def add_project(self, project_data: dict):
        """立项申请"""
        try:
            proj = ResearchProject(**project_data)
            self.db.add(proj)
            self.db.commit()
            return proj
        except Exception as e:
            self.db.rollback()
            raise e

    # --- Read (查) ---
    def get_project(self, project_id: str):
        return self.db.get(ResearchProject, project_id)

    # --- Update (改) ---
    def update_project_status(self, project_id: str, new_status: str):
        """更新项目状态 (如：在研 -> 已结题)"""
        proj = self.db.get(ResearchProject, project_id)
        if proj:
            proj.project_status = new_status
            self.db.commit()
            return proj
        return None

    # --- Delete (删) ---
    def delete_project(self, project_id: str):
        """删除项目 (需注意级联删除相关采集记录和成果)"""
        try:
            # 1. 查找并删除关联的采集记录和成果 (子表)
            self.db.query(ResearchDataCollect).filter_by(project_id=project_id).delete()
            self.db.query(ResearchAchievement).filter_by(project_id=project_id).delete()

            # 2. 删除项目主表
            proj = self.db.get(ResearchProject, project_id)
            if proj:
                self.db.delete(proj)
                self.db.commit()
                return True
        except Exception as e:
            self.db.rollback()
            raise e
        return False


# 如果你需要运行 dao.create_all_tables() 来重新生成表，请导入 dao
if __name__ == '__main__':
    create_all_tables()