-- ============================================================
-- 02_schema.sql —— 业务表 + 系统用户/角色表（以超级用户执行）
-- 所有业务表含通用基础字段：created_by/created_at/updated_by/updated_at/is_enabled/is_deleted
-- 时区统一 Asia/Shanghai（TIMESTAMPTZ）
-- ============================================================

-- 部门
CREATE TABLE IF NOT EXISTS department (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id INTEGER,
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 员工
CREATE TABLE IF NOT EXISTS employee (
    id SERIAL PRIMARY KEY,
    emp_no TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    department_id INTEGER REFERENCES department(id),
    position TEXT,
    staff_type TEXT NOT NULL CHECK (staff_type IN ('内勤','销售','外勤')),
    hire_date DATE,
    status TEXT NOT NULL DEFAULT '在职' CHECK (status IN ('在职','离职')),
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 打卡记录（核心）
CREATE TABLE IF NOT EXISTS attendance_record (
    id BIGSERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id),
    work_date DATE NOT NULL,
    check_in_time TIME,
    check_out_time TIME,
    location TEXT,
    late_minutes INTEGER NOT NULL DEFAULT 0 CHECK (late_minutes >= 0),
    early_minutes INTEGER NOT NULL DEFAULT 0 CHECK (early_minutes >= 0),
    status TEXT NOT NULL CHECK (status IN ('正常','迟到','早退','缺卡','旷工')),
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_attendance UNIQUE (employee_id, work_date)
);
CREATE INDEX IF NOT EXISTS idx_attendance_emp_date ON attendance_record (employee_id, work_date);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance_record (work_date);

-- 请假
CREATE TABLE IF NOT EXISTS leave_record (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id),
    leave_type TEXT NOT NULL CHECK (leave_type IN ('事假','病假','年假','调休')),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_days NUMERIC(6,1),
    reason TEXT,
    status TEXT NOT NULL DEFAULT '待审批' CHECK (status IN ('待审批','通过','驳回')),
    approver TEXT,
    apply_time TIMESTAMPTZ,
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_leave_time CHECK (end_time > start_time)
);

-- 加班
CREATE TABLE IF NOT EXISTS overtime_record (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id),
    overtime_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    overtime_type TEXT NOT NULL CHECK (overtime_type IN ('工作日','周末','法定节假日')),
    hours NUMERIC(5,1),
    status TEXT NOT NULL DEFAULT '待审批' CHECK (status IN ('待审批','通过','驳回')),
    compensation TEXT CHECK (compensation IN ('调休','加班费')),
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_overtime_emp_date ON overtime_record (employee_id, overtime_date);

-- 出差
CREATE TABLE IF NOT EXISTS business_trip (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    destination TEXT,
    task TEXT,
    work_on_weekend INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT '待审批' CHECK (status IN ('待审批','通过','驳回')),
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 补卡
CREATE TABLE IF NOT EXISTS makeup_card (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id),
    work_date DATE NOT NULL,
    reason TEXT,
    apply_time TIMESTAMPTZ,
    overdue INTEGER NOT NULL DEFAULT 0,
    fine NUMERIC(10,2) NOT NULL DEFAULT 0,
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 月度汇总（v1 不灌数据，预留）
CREATE TABLE IF NOT EXISTS attendance_statistics (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee(id),
    stat_month CHAR(7) NOT NULL,
    late_count INTEGER NOT NULL DEFAULT 0,
    early_count INTEGER NOT NULL DEFAULT 0,
    absent_days INTEGER NOT NULL DEFAULT 0,
    overtime_hours NUMERIC(8,1) NOT NULL DEFAULT 0,
    fine_total NUMERIC(10,2) NOT NULL DEFAULT 0,
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 节假日字典
CREATE TABLE IF NOT EXISTS holiday_calendar (
    date DATE PRIMARY KEY,
    name TEXT NOT NULL,
    is_legal_holiday BOOLEAN NOT NULL DEFAULT FALSE,
    is_workday BOOLEAN NOT NULL DEFAULT FALSE,
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 系统用户（登录账号）
CREATE TABLE IF NOT EXISTS sys_user (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    employee_id INTEGER REFERENCES employee(id),
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 角色（权限）
CREATE TABLE IF NOT EXISTS role (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    data_scope TEXT NOT NULL CHECK (data_scope IN ('self','all')),
    description TEXT,
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 用户-角色关联
CREATE TABLE IF NOT EXISTS user_role (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES sys_user(id),
    role_id INTEGER NOT NULL REFERENCES role(id),
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- 会话表（user_id ↔ thread_id 映射；thread_id 即 LangGraph checkpoint 的 key）
CREATE TABLE IF NOT EXISTS chat_session (
    id SERIAL PRIMARY KEY,
    thread_id TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES sys_user(id),
    title TEXT,
    created_by VARCHAR(64), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(64), updated_at TIMESTAMPTZ DEFAULT now(),
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE, is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_chat_session_user ON chat_session (user_id, created_at DESC);
