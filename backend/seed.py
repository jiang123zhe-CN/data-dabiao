from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User
from app.models.directory import Directory
from app.models.field import Field
from app.models.mapping import DirectoryFieldMapping
from app.models.standard import ClassificationCategory, TieringRule
import json


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Users ──
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(username="admin", hashed_password=hash_password("admin123"),
                         role="admin", display_name="系统管理员", email="admin@example.com")
            db.add(admin)
            db.commit()
            print("Default admin user created: admin / admin123")

        sample_users = [
            ("data_entry", "录入员"),
            ("data_admin", "数据管理员"),
            ("reviewer", "复核员"),
        ]
        for role, display_name in sample_users:
            if not db.query(User).filter(User.username == role).first():
                db.add(User(username=role, hashed_password=hash_password("admin123"),
                            role=role, display_name=display_name))
        db.commit()
        print("Sample users seeded.")

        # ── Directories ──
        if db.query(Directory).count() == 0:
            dirs_data = [
                {"name": "客户域", "code": "customer", "description": "客户相关数据资产", "level": 0},
                {"name": "客户基本信息", "code": "customer_base", "description": "客户姓名、证件等基础字段", "level": 1, "parent_code": "customer"},
                {"name": "客户联系信息", "code": "customer_contact", "description": "电话、邮箱、地址等", "level": 1, "parent_code": "customer"},
                {"name": "交易域", "code": "transaction", "description": "交易流水相关", "level": 0},
                {"name": "订单信息", "code": "order", "description": "订单头、订单行", "level": 1, "parent_code": "transaction"},
                {"name": "支付信息", "code": "payment", "description": "支付方式、流水号", "level": 1, "parent_code": "transaction"},
                {"name": "风控域", "code": "risk", "description": "风险控制相关", "level": 0},
                {"name": "反欺诈", "code": "anti_fraud", "description": "欺诈检测数据", "level": 1, "parent_code": "risk"},
            ]
            parent_map = {}
            for d in dirs_data:
                parent_id = None
                if "parent_code" in d:
                    parent_id = parent_map.get(d["parent_code"])
                obj = Directory(name=d["name"], code=d["code"], description=d.get("description", ""),
                                level=d["level"], parent_id=parent_id, created_by=admin.id)
                db.add(obj)
                db.flush()
                parent_map[d["code"]] = obj.id
            db.commit()
            print("Sample directories seeded.")

        # ── Fields ──
        if db.query(Field).count() == 0:
            fields_data = [
                {"field_code": "F001", "name": "客户姓名", "data_type": "VARCHAR", "table_name": "dim_customer", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L2"},
                {"field_code": "F002", "name": "身份证号", "data_type": "VARCHAR", "table_name": "dim_customer", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L4"},
                {"field_code": "F003", "name": "手机号", "data_type": "VARCHAR", "table_name": "dim_customer_contact", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L3"},
                {"field_code": "F004", "name": "邮箱", "data_type": "VARCHAR", "table_name": "dim_customer_contact", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L2"},
                {"field_code": "F005", "name": "订单号", "data_type": "VARCHAR", "table_name": "fact_order", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L2"},
                {"field_code": "F006", "name": "订单金额", "data_type": "DECIMAL", "table_name": "fact_order", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L2"},
                {"field_code": "F007", "name": "支付方式", "data_type": "VARCHAR", "table_name": "dim_payment", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L1"},
                {"field_code": "F008", "name": "交易时间", "data_type": "DATETIME", "table_name": "fact_transaction", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L2"},
                {"field_code": "F009", "name": "设备指纹", "data_type": "VARCHAR", "table_name": "fact_login", "database_name": "ods", "business_domain": "风控域", "sensitivity_level": "L3"},
                {"field_code": "F010", "name": "IP地址", "data_type": "VARCHAR", "table_name": "fact_login", "database_name": "ods", "business_domain": "风控域", "sensitivity_level": "L2"},
            ]
            for f in fields_data:
                db.add(Field(**f, created_by=admin.id))
            db.commit()
            print("Sample fields seeded.")

        # ── Mappings ──
        if db.query(DirectoryFieldMapping).count() == 0:
            dirs = {d.code: d.id for d in db.query(Directory).all()}
            fields = {f.field_code: f.id for f in db.query(Field).all()}
            mappings_data = [
                ("customer_base", "F001"), ("customer_base", "F002"),
                ("customer_contact", "F003"), ("customer_contact", "F004"),
                ("order", "F005"), ("order", "F006"),
                ("payment", "F007"), ("transaction", "F008"),
            ]
            for dir_code, field_code in mappings_data:
                did, fid = dirs.get(dir_code), fields.get(field_code)
                if did and fid:
                    db.add(DirectoryFieldMapping(directory_id=did, field_id=fid,
                                                 mapping_source="manual", created_by=admin.id))
            db.commit()
            print("Sample mappings seeded.")

        # ── Classification Categories (China Financial Standard 8 Categories) ──
        if db.query(ClassificationCategory).count() == 0:
            categories_data = [
                # Level 0: 8 root categories
                {"name": "客户数据", "code": "customer_data", "category_type": "business",
                 "description": "与客户身份、行为、关系相关的数据", "keywords": "客户,用户,账户持有人,借款人",
                 "regulatory_ref": "《个人信息保护法》《金融数据安全 数据安全分级指南》JR/T 0197-2020"},
                {"name": "交易数据", "code": "transaction_data", "category_type": "business",
                 "description": "交易记录、流水、支付等金融活动数据", "keywords": "交易,流水,支付,转账,结算",
                 "regulatory_ref": "《金融数据安全 数据安全分级指南》JR/T 0197-2020"},
                {"name": "产品数据", "code": "product_data", "category_type": "business",
                 "description": "金融产品定义、参数、规则等", "keywords": "产品,利率,费率,条款,额度",
                 "regulatory_ref": "《银行业金融机构数据治理指引》"},
                {"name": "财务数据", "code": "financial_data", "category_type": "business",
                 "description": "机构自身财务、会计、资产负债数据", "keywords": "财务,会计,资产,负债,损益",
                 "regulatory_ref": "《企业会计准则》《金融企业财务规则》"},
                {"name": "运营数据", "code": "operations_data", "category_type": "business",
                 "description": "日常运营、流程、服务相关数据", "keywords": "运营,流程,工单,服务,日志",
                 "regulatory_ref": "《银行业金融机构数据治理指引》"},
                {"name": "风险数据", "code": "risk_data", "category_type": "business",
                 "description": "风险管理、模型、评级、预警数据", "keywords": "风险,评级,模型,预警,不良,拨备",
                 "regulatory_ref": "《银行业金融机构全面风险管理指引》"},
                {"name": "合规数据", "code": "compliance_data", "category_type": "regulatory",
                 "description": "监管报送、反洗钱、合规审查数据", "keywords": "合规,监管,报送,反洗钱,审计,检查",
                 "regulatory_ref": "《反洗钱法》《金融机构大额交易和可疑交易报告管理办法》"},
                {"name": "系统数据", "code": "system_data", "category_type": "technical",
                 "description": "IT基础设施、系统配置、安全管控数据", "keywords": "系统,配置,密钥,证书,网络,权限",
                 "regulatory_ref": "《网络安全法》《信息安全技术 网络安全等级保护基本要求》"},
            ]
            parent_map: dict[str, int] = {}
            for d in categories_data:
                obj = ClassificationCategory(
                    name=d["name"], code=d["code"], level=0,
                    category_type=d["category_type"], description=d.get("description", ""),
                    keywords=d.get("keywords", ""), regulatory_ref=d.get("regulatory_ref", ""),
                    created_by=admin.id,
                )
                db.add(obj)
                db.flush()
                parent_map[d["code"]] = obj.id

            # Level 1: sub-categories
            sub_categories = [
                {"name": "客户基本信息", "code": "customer_base_info", "parent_code": "customer_data",
                 "description": "姓名、证件、性别、出生日期等基础身份字段", "keywords": "姓名,证件,身份证,性别,出生日期"},
                {"name": "客户联系信息", "code": "customer_contact_info", "parent_code": "customer_data",
                 "description": "电话、邮箱、地址等联系方式", "keywords": "手机,电话,邮箱,地址,微信"},
                {"name": "客户标识信息", "code": "customer_identity", "parent_code": "customer_data",
                 "description": "生物特征、设备指纹等唯一标识", "keywords": "指纹,人脸,声纹,设备指纹,IP"},
                {"name": "客户行为数据", "code": "customer_behavior", "parent_code": "customer_data",
                 "description": "浏览、点击、偏好、消费习惯等行为数据", "keywords": "行为,偏好,浏览,点击,消费习惯"},
                {"name": "交易明细", "code": "transaction_detail", "parent_code": "transaction_data",
                 "description": "单笔交易的时间、金额、对手方等", "keywords": "金额,对手方,时间,币种,渠道"},
                {"name": "支付结算", "code": "payment_settlement", "parent_code": "transaction_data",
                 "description": "支付方式、清算、结算数据", "keywords": "支付,清算,结算,账户,路由"},
                {"name": "风险模型参数", "code": "risk_model_params", "parent_code": "risk_data",
                 "description": "风控模型的权重、阈值、策略参数", "keywords": "模型,权重,阈值,策略,参数,算法"},
                {"name": "风险预警信号", "code": "risk_alert", "parent_code": "risk_data",
                 "description": "风险事件、预警规则触发记录", "keywords": "预警,告警,异常,触发,黑名单"},
                {"name": "监管报送数据", "code": "regulatory_reporting", "parent_code": "compliance_data",
                 "description": "1104、EAST、反洗钱等监管报送数据", "keywords": "1104,EAST,反洗钱,大额,可疑"},
                {"name": "系统安全配置", "code": "system_security", "parent_code": "system_data",
                 "description": "密钥、证书、权限策略等安全保障数据", "keywords": "密钥,证书,密码,权限,Token"},
            ]
            for d in sub_categories:
                parent_id = parent_map.get(d["parent_code"])
                if parent_id:
                    obj = ClassificationCategory(
                        name=d["name"], code=d["code"], level=1,
                        category_type="business", description=d.get("description", ""),
                        keywords=d.get("keywords", ""), parent_id=parent_id,
                        created_by=admin.id,
                    )
                    db.add(obj)
            db.commit()
            print("Classification categories seeded (8 roots + 10 sub).")

        # ── Tiering Rules (L1-L4) ──
        if db.query(TieringRule).count() == 0:
            tier_rules = [
                {
                    "tier_level": "L4", "tier_name": "机密/严格保密",
                    "rule_type": "regex",
                    "rule_content": json.dumps({
                        "keywords": ["身份证号", "银行卡号", "密码", "密钥", "生物特征", "模型权重", "策略参数",
                                     "账户密码", "数字证书", "私钥", "Token", "票据"],
                        "patterns": [r"\d{17}[\dXx]", r"\b\d{16,19}\b"],
                        "metadata_rules": {"sensitivity_level": "L4"},
                    }, ensure_ascii=False),
                    "priority": 100,
                    "regulatory_basis": "《个人信息保护法》第28条 敏感个人信息",
                },
                {
                    "tier_level": "L3", "tier_name": "敏感",
                    "rule_type": "regex",
                    "rule_content": json.dumps({
                        "keywords": ["手机号", "邮箱", "地址", "设备指纹", "交易金额", "账户号", "IP地址",
                                     "身份证", "手机", "电话", "住址", "账户", "卡号"],
                        "patterns": [r"1[3-9]\d{9}", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                                    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"],
                        "metadata_rules": {"sensitivity_level": "L3"},
                    }, ensure_ascii=False),
                    "priority": 80,
                    "regulatory_basis": "《个人信息保护法》第4条 个人信息处理",
                },
                {
                    "tier_level": "L2", "tier_name": "内部",
                    "rule_type": "keyword",
                    "rule_content": json.dumps({
                        "keywords": ["交易时间", "订单号", "支付方式", "客户姓名", "内部报表", "运营数据",
                                     "流程", "工单", "产品名称", "费用", "利率"],
                        "metadata_rules": {"sensitivity_level": "L2"},
                    }, ensure_ascii=False),
                    "priority": 60,
                    "regulatory_basis": "《数据安全法》第21条 数据分类分级制度",
                },
                {
                    "tier_level": "L1", "tier_name": "公开",
                    "rule_type": "keyword",
                    "rule_content": json.dumps({
                        "keywords": ["产品说明", "公告", "新闻", "公开", "描述", "备注", "说明",
                                     "产品类型", "业务类型", "状态", "标志", "类型"],
                        "metadata_rules": {"sensitivity_level": "L1"},
                    }, ensure_ascii=False),
                    "priority": 40,
                    "regulatory_basis": "《数据安全法》第21条",
                },
            ]
            for r in tier_rules:
                db.add(TieringRule(**r, created_by=admin.id))
            db.commit()
            print("Tiering rules seeded (L1-L4).")

        print("Seed completed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
