"""表结构提供器：两阶段 Schema 选择（避免全量表结构占满 LLM 上下文）。

阶段一：get_simple_schema() 返回「表名 + 一句简介」的轻量概述，供 LLM 选表。
阶段二：get_detail_schema(tables) 按选中的表返回「表说明 + 逐列说明 + 枚举」的详细结构。

表/列说明与数据库 COMMENT（sql/04_comments.sql）保持一致，便于维护与 LLM 理解。

TODO:
- 未来表规模再增大时，阶段一升级为向量语义召回（VectorSchemaProvider）。
- 未来接入「示例 SQL 召回」：构造 问题→SQL 示例库，支持手动录入 + 历史问答记录上传到向量库，
  按问题语义召回最相关示例 SQL 作为 few-shot，提升复杂 SQL 生成准确率（FewShotRetriever）。
"""
from typing import Protocol

# 表名白名单（阶段一选表结果只允许落在白名单内）
TABLE_NAMES = {
    "v_department",
    "v_employee",
    "v_attendance_record",
    "v_leave_record",
    "v_overtime_record",
    "v_business_trip",
    "v_makeup_card",
    "v_holiday_calendar",
}

# 阶段一：轻量概述（表名 + 一句简介）
TABLE_OVERVIEW = [
    ("v_employee", "员工信息（工号/姓名/部门/岗位/员工类型/在职状态）"),
    ("v_attendance_record", "打卡记录（日期/上下班时间/迟到早退分钟数/考勤状态）"),
    ("v_leave_record", "请假记录（假别/起止/时长/事由/审批状态）"),
    ("v_overtime_record", "加班记录（日期/加班类型/时长/补偿方式）"),
    ("v_business_trip", "出差记录（起止日期/地点/任务/周日是否工作）"),
    ("v_makeup_card", "补卡记录（日期/事由/是否超时/罚款）"),
    ("v_holiday_calendar", "节假日日历（是否法定/是否补班）"),
    ("v_department", "部门（名称/上级部门）"),
]

# 表关系（阶段一选表时一并提供给 LLM，便于理解表之间的连接）
TABLE_RELATIONS = (
    "【表关系】\n"
    "- 员工维度：v_employee.id ← v_attendance_record / v_leave_record / v_overtime_record / v_business_trip / v_makeup_card 的 employee_id\n"
    "- 部门维度：v_employee.department_id → v_department.id\n"
    "- 部门层级：v_department.parent_id → v_department.id（自关联）\n"
    "- 关联查询示例：查某人考勤 = v_employee JOIN v_attendance_record ON v_employee.id = v_attendance_record.employee_id"
)

# 阶段二：分表详细结构（表说明 + 逐列说明 + 枚举）
TABLE_DETAILS = {
    "v_department": (
        "【v_department 部门表】公司组织架构部门信息。\n"
        "列：id=部门ID(主键)；name=部门名称；parent_id=上级部门ID(顶级为NULL)"
    ),
    "v_employee": (
        "【v_employee 员工表】员工基本信息与考勤身份。\n"
        "列：id=员工ID(主键，各业务表 employee_id 均关联此列)；emp_no=工号(唯一)；name=姓名；"
        "department_id=所属部门ID；position=岗位；"
        "staff_type=员工类型(内勤/销售/外勤；销售、外勤拜访客户超时不算加班)；"
        "hire_date=入职日期；status=在职状态(在职/离职)"
    ),
    "v_attendance_record": (
        "【v_attendance_record 打卡记录表】员工每日上下班打卡与迟到/早退/旷工判定（每工作日一行）。\n"
        "列：id=记录ID；employee_id=员工ID；work_date=考勤日期；"
        "check_in_time=上班打卡时间(缺卡为空)；check_out_time=下班打卡时间(缺卡为空)；"
        "location=签到地点；late_minutes=迟到分钟数(0=未迟到，>=30按旷工)；"
        "early_minutes=早退分钟数(0=未早退，>=30按旷工)；"
        "status=考勤状态(正常/迟到/早退/缺卡/旷工)"
    ),
    "v_leave_record": (
        "【v_leave_record 请假表】员工请假申请与审批记录。\n"
        "列：id=记录ID；employee_id=员工ID；leave_type=假别(事假/病假/年假/调休)；"
        "start_time=请假开始时间；end_time=请假结束时间；duration_days=请假时长(天)；"
        "reason=请假事由；status=审批状态(待审批/通过/驳回)；approver=审批人；"
        "apply_time=申请时间(制度要求提前一天申请)"
    ),
    "v_overtime_record": (
        "【v_overtime_record 加班表】加班申请与审批记录（类型决定补偿倍率）。\n"
        "列：id=记录ID；employee_id=员工ID；overtime_date=加班日期；"
        "start_time=加班开始时间；end_time=加班结束时间；"
        "overtime_type=加班类型(工作日/周末/法定节假日；周末含周六周日)；"
        "hours=加班时长(小时)；status=审批状态(待审批/通过/驳回)；"
        "compensation=补偿方式(调休/加班费；周末优先调休1:1，法定300%不调休)"
    ),
    "v_business_trip": (
        "【v_business_trip 出差表】员工出差申请与考勤记录。\n"
        "列：id=记录ID；employee_id=员工ID；start_date=出差开始日期；end_date=出差结束日期；"
        "destination=出差地点；task=出差任务；"
        "work_on_weekend=周日是否安排工作(0否/1是；是则可申请调休1:1)；"
        "status=审批状态(待审批/通过/驳回)"
    ),
    "v_makeup_card": (
        "【v_makeup_card 补卡表】忘记/无法打卡的补卡申请记录。\n"
        "列：id=记录ID；employee_id=员工ID；work_date=补卡对应的考勤日期；reason=补卡事由；"
        "apply_time=申请时间(制度要求2日内完成)；overdue=是否超时(0否/1是，超时罚50元)；"
        "fine=罚款金额(超时=50，正常=0)"
    ),
    "v_holiday_calendar": (
        "【v_holiday_calendar 节假日字典表】法定节假日与调休补班（工作日判定依赖此表完整性）。\n"
        "列：date=日期(主键)；name=节假日名称；is_legal_holiday=是否法定节假日(true/false)；"
        "is_workday=是否调休补班日(true/false)"
    ),
}

FOOTER = (
    "\n\n【工作日判定】仅当用户问题明确涉及“工作日/周末/周日/节假日”时才按星期过滤；用户只问“加班/迟到”等一般问题时，不要添加星期过滤。\n"
    "- 工作日 = 周一至周六；非工作日 = 周日 + 法定节假日（调休补班日除外）。\n"
    "- 星期判断用 EXTRACT(DOW FROM date)：0=周日、1=周一、…、6=周六；即工作日 DOW IN (1,2,3,4,5,6)，非工作日 DOW = 0。\n"
    "- 法定节假日：v_holiday_calendar.is_legal_holiday=TRUE 为非工作日；调休补班日 is_workday=TRUE 为工作日。\n"
    "【罚款口径】迟到/早退 <10 分钟罚 5 元；[10,20) 罚 10 元；[20,30) 罚 20 元；≥30 分钟按旷工。\n"
    "【加班补偿】周末优先调休 1:1（无法调休 200%）；法定节假日 300% 不调休；调休余额 8 小时=1 天。"
)


class SchemaProvider(Protocol):
    def get_simple_schema(self) -> str: ...
    def get_detail_schema(self, tables: list[str]) -> str: ...


class TwoStageSchemaProvider:
    def get_simple_schema(self) -> str:
        overview = "\n".join(f"- {name}：{desc}" for name, desc in TABLE_OVERVIEW)
        return overview + "\n\n" + TABLE_RELATIONS

    def get_detail_schema(self, tables: list[str]) -> str:
        chosen = [t for t in tables if t in TABLE_DETAILS]
        if not chosen:  # 选表失败兜底：返回全部（保证可用）
            chosen = [name for name, _ in TABLE_OVERVIEW]
        detail = "\n".join(TABLE_DETAILS[t] for t in chosen)
        # 阶段二同样附上表关系，供 SQL 生成时正确 JOIN
        return detail + "\n\n" + TABLE_RELATIONS + FOOTER


# 全局单例
schema_provider: SchemaProvider = TwoStageSchemaProvider()
