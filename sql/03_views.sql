-- ============================================================
-- 03_views.sql —— 软删除视图（业务数据只查视图，不查基表）+ 授权
-- ============================================================

CREATE OR REPLACE VIEW v_department AS
    SELECT * FROM department WHERE is_deleted = FALSE AND is_enabled = TRUE;

CREATE OR REPLACE VIEW v_employee AS
    SELECT * FROM employee WHERE is_deleted = FALSE AND is_enabled = TRUE;

CREATE OR REPLACE VIEW v_attendance_record AS
    SELECT * FROM attendance_record WHERE is_deleted = FALSE AND is_enabled = TRUE;

CREATE OR REPLACE VIEW v_leave_record AS
    SELECT * FROM leave_record WHERE is_deleted = FALSE AND is_enabled = TRUE;

CREATE OR REPLACE VIEW v_overtime_record AS
    SELECT * FROM overtime_record WHERE is_deleted = FALSE AND is_enabled = TRUE;

CREATE OR REPLACE VIEW v_business_trip AS
    SELECT * FROM business_trip WHERE is_deleted = FALSE AND is_enabled = TRUE;

CREATE OR REPLACE VIEW v_makeup_card AS
    SELECT * FROM makeup_card WHERE is_deleted = FALSE AND is_enabled = TRUE;

CREATE OR REPLACE VIEW v_holiday_calendar AS
    SELECT * FROM holiday_calendar WHERE is_deleted = FALSE AND is_enabled = TRUE;

-- ============ 授权 ============
-- app_ro：业务数据只读视图 + 登录鉴权所需的用户/角色表（受控代码路径，参数化查询）
GRANT USAGE ON SCHEMA public TO app_ro;
GRANT SELECT ON v_department, v_employee, v_attendance_record, v_leave_record,
    v_overtime_record, v_business_trip, v_makeup_card, v_holiday_calendar TO app_ro;
GRANT SELECT ON sys_user, role, user_role TO app_ro;

-- app_rw：仅供 LangGraph checkpointer 建表/读写状态 + chat_session 会话读写
GRANT USAGE, CREATE ON SCHEMA public TO app_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON chat_session TO app_rw;
GRANT USAGE ON SEQUENCE chat_session_id_seq TO app_rw;
