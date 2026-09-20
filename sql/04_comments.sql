-- ============================================================
-- 04_comments.sql —— 表/字段注释（COMMENT ON）
-- 用途：1) 便于后期维护；2) 供 LLM 选表、生成 SQL 参考的详细说明
-- 幂等：可重复执行（覆盖更新）
-- ============================================================

-- ---------- department 部门表 ----------
COMMENT ON TABLE department IS '部门表：公司组织架构部门信息';
COMMENT ON COLUMN department.id IS '部门ID（主键）';
COMMENT ON COLUMN department.name IS '部门名称';
COMMENT ON COLUMN department.parent_id IS '上级部门ID（支持层级，顶级为 NULL）';

-- ---------- employee 员工表 ----------
COMMENT ON TABLE employee IS '员工表：员工基本信息与考勤身份（内勤/销售/外勤）';
COMMENT ON COLUMN employee.id IS '员工ID（主键，业务表 employee_id 均关联此列）';
COMMENT ON COLUMN employee.emp_no IS '工号（唯一）';
COMMENT ON COLUMN employee.name IS '姓名';
COMMENT ON COLUMN employee.department_id IS '所属部门ID（关联 department.id）';
COMMENT ON COLUMN employee.position IS '岗位';
COMMENT ON COLUMN employee.staff_type IS '员工类型：内勤/销售/外勤（销售、外勤拜访客户超时不算加班）';
COMMENT ON COLUMN employee.hire_date IS '入职日期';
COMMENT ON COLUMN employee.status IS '在职状态：在职/离职';

-- ---------- attendance_record 打卡记录表 ----------
COMMENT ON TABLE attendance_record IS '打卡记录表：员工每日上下班打卡与迟到/早退/旷工判定（每工作日一行）';
COMMENT ON COLUMN attendance_record.id IS '记录ID（主键）';
COMMENT ON COLUMN attendance_record.employee_id IS '员工ID（关联 employee.id）';
COMMENT ON COLUMN attendance_record.work_date IS '考勤日期';
COMMENT ON COLUMN attendance_record.check_in_time IS '上班打卡时间（缺卡为空）';
COMMENT ON COLUMN attendance_record.check_out_time IS '下班打卡时间（缺卡为空）';
COMMENT ON COLUMN attendance_record.location IS '签到地点（企业微信签到点/外勤备注）';
COMMENT ON COLUMN attendance_record.late_minutes IS '迟到分钟数（0=未迟到；>=30 按旷工）';
COMMENT ON COLUMN attendance_record.early_minutes IS '早退分钟数（0=未早退；>=30 按旷工）';
COMMENT ON COLUMN attendance_record.status IS '考勤状态：正常/迟到/早退/缺卡/旷工';

-- ---------- leave_record 请假表 ----------
COMMENT ON TABLE leave_record IS '请假表：员工请假申请与审批记录';
COMMENT ON COLUMN leave_record.id IS '记录ID（主键）';
COMMENT ON COLUMN leave_record.employee_id IS '员工ID（关联 employee.id）';
COMMENT ON COLUMN leave_record.leave_type IS '假别：事假/病假/年假/调休';
COMMENT ON COLUMN leave_record.start_time IS '请假开始时间';
COMMENT ON COLUMN leave_record.end_time IS '请假结束时间';
COMMENT ON COLUMN leave_record.duration_days IS '请假时长（天）';
COMMENT ON COLUMN leave_record.reason IS '请假事由';
COMMENT ON COLUMN leave_record.status IS '审批状态：待审批/通过/驳回';
COMMENT ON COLUMN leave_record.approver IS '审批人';
COMMENT ON COLUMN leave_record.apply_time IS '申请时间（制度要求提前一天申请）';

-- ---------- overtime_record 加班表 ----------
COMMENT ON TABLE overtime_record IS '加班表：加班申请与审批记录（类型决定补偿倍率）';
COMMENT ON COLUMN overtime_record.id IS '记录ID（主键）';
COMMENT ON COLUMN overtime_record.employee_id IS '员工ID（关联 employee.id）';
COMMENT ON COLUMN overtime_record.overtime_date IS '加班日期';
COMMENT ON COLUMN overtime_record.start_time IS '加班开始时间';
COMMENT ON COLUMN overtime_record.end_time IS '加班结束时间';
COMMENT ON COLUMN overtime_record.overtime_type IS '加班类型：工作日/周末/法定节假日（周末含周六周日）';
COMMENT ON COLUMN overtime_record.hours IS '加班时长（小时）';
COMMENT ON COLUMN overtime_record.status IS '审批状态：待审批/通过/驳回（制度要求提前审批并抄送考勤员）';
COMMENT ON COLUMN overtime_record.compensation IS '补偿方式：调休/加班费（周末优先调休1:1，法定300%不调休）';

-- ---------- business_trip 出差表 ----------
COMMENT ON TABLE business_trip IS '出差表：员工出差申请与考勤记录';
COMMENT ON COLUMN business_trip.id IS '记录ID（主键）';
COMMENT ON COLUMN business_trip.employee_id IS '员工ID（关联 employee.id）';
COMMENT ON COLUMN business_trip.start_date IS '出差开始日期';
COMMENT ON COLUMN business_trip.end_date IS '出差结束日期';
COMMENT ON COLUMN business_trip.destination IS '出差地点';
COMMENT ON COLUMN business_trip.task IS '出差任务';
COMMENT ON COLUMN business_trip.work_on_weekend IS '周日是否安排工作：0否/1是（是则可申请调休1:1）';
COMMENT ON COLUMN business_trip.status IS '审批状态：待审批/通过/驳回';

-- ---------- makeup_card 补卡表 ----------
COMMENT ON TABLE makeup_card IS '补卡表：忘记/无法打卡的补卡申请记录';
COMMENT ON COLUMN makeup_card.id IS '记录ID（主键）';
COMMENT ON COLUMN makeup_card.employee_id IS '员工ID（关联 employee.id）';
COMMENT ON COLUMN makeup_card.work_date IS '补卡对应的考勤日期';
COMMENT ON COLUMN makeup_card.reason IS '补卡事由';
COMMENT ON COLUMN makeup_card.apply_time IS '申请时间（制度要求 2 日内完成）';
COMMENT ON COLUMN makeup_card.overdue IS '是否超时：0否/1是（超时走通用审批并罚50元）';
COMMENT ON COLUMN makeup_card.fine IS '罚款金额（超时=50，正常=0）';

-- ---------- attendance_statistics 月度汇总表 ----------
COMMENT ON TABLE attendance_statistics IS '月度考勤汇总表（可选，v1 不启用，统计走实时聚合）';
COMMENT ON COLUMN attendance_statistics.id IS '记录ID（主键）';
COMMENT ON COLUMN attendance_statistics.employee_id IS '员工ID（关联 employee.id）';
COMMENT ON COLUMN attendance_statistics.stat_month IS '统计月份（如 2026-01）';
COMMENT ON COLUMN attendance_statistics.late_count IS '迟到次数';
COMMENT ON COLUMN attendance_statistics.early_count IS '早退次数';
COMMENT ON COLUMN attendance_statistics.absent_days IS '旷工天数';
COMMENT ON COLUMN attendance_statistics.overtime_hours IS '加班时长（小时）';
COMMENT ON COLUMN attendance_statistics.fine_total IS '罚款合计（元）';

-- ---------- holiday_calendar 节假日字典表 ----------
COMMENT ON TABLE holiday_calendar IS '节假日字典表：法定节假日与调休补班（工作日判定依赖此表完整性）';
COMMENT ON COLUMN holiday_calendar.date IS '日期（主键）';
COMMENT ON COLUMN holiday_calendar.name IS '节假日名称';
COMMENT ON COLUMN holiday_calendar.is_legal_holiday IS '是否法定节假日：true/false';
COMMENT ON COLUMN holiday_calendar.is_workday IS '是否调休补班日：true/false';

-- ---------- sys_user 系统用户表 ----------
COMMENT ON TABLE sys_user IS '系统用户表：登录账号（员工绑定 employee_id，管理员为 NULL）';
COMMENT ON COLUMN sys_user.id IS '用户ID（主键，RBAC 身份锚点 user_id）';
COMMENT ON COLUMN sys_user.username IS '登录名（唯一）';
COMMENT ON COLUMN sys_user.password_hash IS '密码哈希（演示 sha256）';
COMMENT ON COLUMN sys_user.display_name IS '显示名（姓名/管理员）';
COMMENT ON COLUMN sys_user.employee_id IS '绑定员工ID（管理员为 NULL，不打卡）';
COMMENT ON COLUMN sys_user.is_admin IS '是否管理员：true/false';

-- ---------- role 角色表 ----------
COMMENT ON TABLE role IS '角色（权限）表：定义数据范围';
COMMENT ON COLUMN role.id IS '角色ID（主键）';
COMMENT ON COLUMN role.code IS '角色编码：admin/employee';
COMMENT ON COLUMN role.name IS '角色名：管理员/普通员工';
COMMENT ON COLUMN role.data_scope IS '数据范围：self（仅本人）/all（全局）';
COMMENT ON COLUMN role.description IS '角色说明';

-- ---------- user_role 用户-角色关联表 ----------
COMMENT ON TABLE user_role IS '用户-角色关联表（多对多）';
COMMENT ON COLUMN user_role.id IS '记录ID（主键）';
COMMENT ON COLUMN user_role.user_id IS '用户ID（关联 sys_user.id）';
COMMENT ON COLUMN user_role.role_id IS '角色ID（关联 role.id）';

-- ---------- 通用基础字段（所有业务表统一，逐表标注） ----------
COMMENT ON COLUMN department.created_by IS '创建人';
COMMENT ON COLUMN department.created_at IS '创建时间';
COMMENT ON COLUMN department.updated_by IS '修改人';
COMMENT ON COLUMN department.updated_at IS '修改时间';
COMMENT ON COLUMN department.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN department.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN employee.created_by IS '创建人';
COMMENT ON COLUMN employee.created_at IS '创建时间';
COMMENT ON COLUMN employee.updated_by IS '修改人';
COMMENT ON COLUMN employee.updated_at IS '修改时间';
COMMENT ON COLUMN employee.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN employee.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN attendance_record.created_by IS '创建人';
COMMENT ON COLUMN attendance_record.created_at IS '创建时间';
COMMENT ON COLUMN attendance_record.updated_by IS '修改人';
COMMENT ON COLUMN attendance_record.updated_at IS '修改时间';
COMMENT ON COLUMN attendance_record.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN attendance_record.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN leave_record.created_by IS '创建人';
COMMENT ON COLUMN leave_record.created_at IS '创建时间';
COMMENT ON COLUMN leave_record.updated_by IS '修改人';
COMMENT ON COLUMN leave_record.updated_at IS '修改时间';
COMMENT ON COLUMN leave_record.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN leave_record.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN overtime_record.created_by IS '创建人';
COMMENT ON COLUMN overtime_record.created_at IS '创建时间';
COMMENT ON COLUMN overtime_record.updated_by IS '修改人';
COMMENT ON COLUMN overtime_record.updated_at IS '修改时间';
COMMENT ON COLUMN overtime_record.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN overtime_record.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN business_trip.created_by IS '创建人';
COMMENT ON COLUMN business_trip.created_at IS '创建时间';
COMMENT ON COLUMN business_trip.updated_by IS '修改人';
COMMENT ON COLUMN business_trip.updated_at IS '修改时间';
COMMENT ON COLUMN business_trip.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN business_trip.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN makeup_card.created_by IS '创建人';
COMMENT ON COLUMN makeup_card.created_at IS '创建时间';
COMMENT ON COLUMN makeup_card.updated_by IS '修改人';
COMMENT ON COLUMN makeup_card.updated_at IS '修改时间';
COMMENT ON COLUMN makeup_card.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN makeup_card.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN attendance_statistics.created_by IS '创建人';
COMMENT ON COLUMN attendance_statistics.created_at IS '创建时间';
COMMENT ON COLUMN attendance_statistics.updated_by IS '修改人';
COMMENT ON COLUMN attendance_statistics.updated_at IS '修改时间';
COMMENT ON COLUMN attendance_statistics.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN attendance_statistics.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN holiday_calendar.created_by IS '创建人';
COMMENT ON COLUMN holiday_calendar.created_at IS '创建时间';
COMMENT ON COLUMN holiday_calendar.updated_by IS '修改人';
COMMENT ON COLUMN holiday_calendar.updated_at IS '修改时间';
COMMENT ON COLUMN holiday_calendar.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN holiday_calendar.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN sys_user.created_by IS '创建人';
COMMENT ON COLUMN sys_user.created_at IS '创建时间';
COMMENT ON COLUMN sys_user.updated_by IS '修改人';
COMMENT ON COLUMN sys_user.updated_at IS '修改时间';
COMMENT ON COLUMN sys_user.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN sys_user.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN role.created_by IS '创建人';
COMMENT ON COLUMN role.created_at IS '创建时间';
COMMENT ON COLUMN role.updated_by IS '修改人';
COMMENT ON COLUMN role.updated_at IS '修改时间';
COMMENT ON COLUMN role.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN role.is_deleted IS '删除标志（软删除）：true已删除/false正常';
COMMENT ON COLUMN user_role.created_by IS '创建人';
COMMENT ON COLUMN user_role.created_at IS '创建时间';
COMMENT ON COLUMN user_role.updated_by IS '修改人';
COMMENT ON COLUMN user_role.updated_at IS '修改时间';
COMMENT ON COLUMN user_role.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN user_role.is_deleted IS '删除标志（软删除）：true已删除/false正常';

-- ---------- chat_session 会话表 ----------
COMMENT ON TABLE chat_session IS '会话表：user_id 与 LangGraph thread_id 的映射（多轮会话归属）';
COMMENT ON COLUMN chat_session.id IS '会话ID（主键）';
COMMENT ON COLUMN chat_session.thread_id IS 'LangGraph checkpoint 的 thread_id（唯一）';
COMMENT ON COLUMN chat_session.user_id IS '所属用户ID（关联 sys_user.id，员工/管理员各自会话隔离）';
COMMENT ON COLUMN chat_session.title IS '会话标题（首条消息截断）';
COMMENT ON COLUMN chat_session.created_by IS '创建人';
COMMENT ON COLUMN chat_session.created_at IS '创建时间';
COMMENT ON COLUMN chat_session.updated_by IS '修改人';
COMMENT ON COLUMN chat_session.updated_at IS '修改时间';
COMMENT ON COLUMN chat_session.is_enabled IS '启用标志：true启用/false停用';
COMMENT ON COLUMN chat_session.is_deleted IS '删除标志（软删除）：true已删除/false正常';
