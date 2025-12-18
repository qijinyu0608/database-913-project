# 国家公园智慧管理系统 (National Park Smart Management System)

这是一个基于 Python Flask 和 SQL Server 构建的综合性国家公园管理平台。系统集成了生物多样性监测、生态环境感知、游客智能管理、执法监管及科研数据支撑五大核心业务模块，并实现了基于角色（RBAC）的精细化权限管理。

## 📖 项目简介

本项目旨在为国家公园提供全方位的数字化管理解决方案。通过统一的 Web 界面，不同角色的用户（如管理员、监测员、执法人员、游客等）可以访问各自相关的业务功能，实现数据的高效采集、管理和分析。

### 核心功能模块

1.  **生物多样性监测 (Bio-Diversity)**
    *   管理物种信息、栖息地信息。
    *   记录和查询生物监测数据。
    *   维护设备与物种关联。

2.  **生态环境感知 (Environment)**
    *   环境监测数据的实时采集与录入。
    *   自动判定环境数据质量（优/差）。
    *   管理监测指标与设备。

3.  **游客智能管理 (Visitor)**
    *   游客预约系统（支持线上预约）。
    *   入园核验与流量控制（限流/预警）。
    *   游客轨迹追踪与行为分析。

4.  **执法监管 (Law Enforcement)**
    *   非法行为的上报与记录。
    *   执法调度派单与处置流程管理。
    *   执法设备与视频监控管理。

5.  **科研数据支撑 (Research)**
    *   科研项目立项与全生命周期管理。
    *   野外数据采集与科研成果归档。
    *   科研人员管理。

### 安全与权限体系

*   **RBAC 模型**: 支持 系统管理员、公园管理人员、生态监测员、数据分析师、游客、执法人员、科研人员 等多种角色。
*   **统一认证**: 支持不同用户类型（员工、游客、执法人员等）通过统一入口登录，系统自动识别身份。
*   **会话管理**: 基于 Server-side Session 的安全会话机制。

## 🛠️ 技术栈

*   **后端**: Python 3.x, Flask
*   **数据库**: Microsoft SQL Server
*   **ORM**: SQLAlchemy
*   **驱动**: pyodbc (ODBC Driver 17 for SQL Server)
*   **前端**: Bootstrap 5, Jinja2 模板
*   **其他**: hashlib (加密), datetime

## 🚀 快速开始

### 1. 环境准备

确保你的系统已安装 Python 3.8+ 和 SQL Server 数据库。

安装 Python 依赖：

```bash
pip install flask sqlalchemy pyodbc
```

*注意：连接 SQL Server 需要安装对应的 ODBC Driver (通常是 ODBC Driver 17 for SQL Server)。*

### 2. 数据库配置

1.  确保 SQL Server 服务正在运行。
2.  修改 `db_config.py` 文件，更新数据库连接字符串以匹配你的本地环境：

```python
# db_config.py (示例)
SQLALCHEMY_DATABASE_URI = 'mssql+pyodbc://用户名:密码@服务器地址/数据库名?driver=ODBC+Driver+17+for+SQL+Server'
```

3.  初始化数据库（建表）：

```bash
python dao.py
# 或者运行 init_db.py (如果包含初始化逻辑)
```
*注：需确保数据库中已预置了必要的基础数据（如管理员账号），或者通过脚本手动插入。*

### 3. 运行应用

在项目根目录下运行：

```bash
python app.py
```

应用将在 `http://127.0.0.1:5001` 启动。

## 📂 项目结构

```text
E:\c\database\project\整合\课设小组任务\数据库全栈web\
├── app.py              # 应用入口，包含路由、权限控制、登录逻辑
├── models.py           # SQLAlchemy ORM 模型定义
├── dao.py              # 数据访问层，封装 CRUD 操作
├── db_config.py        # 数据库连接配置
├── security_manager.py # (可选) 安全相关逻辑
├── static/             # 静态资源 (CSS, JS)
├── templates/          # HTML 模板
│   ├── login.html      # 登录页
│   ├── index.html      # 首页仪表盘
│   ├── layout.html     # 全局布局
│   └── ...             # 各业务模块页面
└── 代码说明             # 详细的设计文档
```

## 🔑 登录说明

系统根据 **用户ID前缀** 自动识别角色（密码需在数据库中预置哈希值）：

*   **超级管理员**: ID `ROOT`
*   **游客**: 前缀 `VI-` (如 `VI-8888-7777` 为演示只读访客)
*   **执法人员**: 前缀 `LE-`
*   **科研人员**: 前缀 `RE-`
*   **普通员工**: 其他 ID (如系统管理员、监测员等)

## 📝 开发规范

*   **数据操作**: 优先使用 `dao.py` 中的 `UniversalDAO` 进行基础增删改查，复杂业务逻辑使用专用 DAO 类。
*   **权限控制**: 在路由上使用 `@require_role([...])` 装饰器进行权限保护。
*   **前端交互**: 尽量使用 `generic` 路由处理通用的数据提交，减少重复代码。

---
*Created for Database Course Project.*
