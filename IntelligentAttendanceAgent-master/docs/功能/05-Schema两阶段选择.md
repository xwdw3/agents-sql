# 功能：Schema 两阶段选择（Schema Provider）

## 定位
避免把全量表结构一次性塞给 LLM：阶段一按"表名+简介+表关系"选表，阶段二按选中表取"表说明+逐列说明+枚举+表关系+口径"生成 SQL。

## 涉及文件
- `app/db/schema_provider.py` — `TwoStageSchemaProvider`、`TABLE_OVERVIEW` / `TABLE_RELATIONS` / `TABLE_DETAILS` / `FOOTER`、`TABLE_NAMES`
- `app/prompts.py` — `TABLE_SELECT_PROMPT`
- `app/schemas.py` — `TableSelectResult`

## 核心逻辑
1. `get_simple_schema()`：表名 + 一句简介 + `【表关系】`（外键：employee_id → v_employee.id 等）。
2. `schema_select_node`：LLM 结构化选表 → **白名单硬过滤**（只保留 `TABLE_NAMES`）。
3. `get_detail_schema(tables)`：选中表的"表说明 + 逐列说明 + 枚举" + `【表关系】` + `【工作日判定】/【罚款口径】/【加班补偿】` footer。

## 关键设计点
- 表/列说明与数据库 `COMMENT`（04_comments.sql）保持一致。
- **工作日判定规则**明确写在 footer：工作日=周一至周六（`DOW IN 1..6`），非工作日=周日（`DOW=0`）+ 法定节假日；且注明"仅当用户明确问工作日/周末时才按星期过滤"。
- 选表失败兜底返回全量详情（保证可用）。
- 未来迭代：阶段一升级向量语义召回（`VectorSchemaProvider`）；示例 SQL 召回（`FewShotRetriever`，向量库 few-shot）。

## 依赖
- `app/db/schema_provider.py` 自身 + `app/schemas.py`。
