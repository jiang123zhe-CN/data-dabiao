from datetime import datetime, timezone
import json

from sqlalchemy.orm import Session

from app.models.field import Field
from app.models.standard import ClassificationCategory, TieringRule
from app.models.tagging import TaggingHistory
from app.services.rule_engine import RuleEngine
from app.services.llm_service import classify_field_with_ai


class TaggingPipeline:
    """Orchestrates the full tagging pipeline:
    Data Collection -> Rule Engine -> AI Analysis -> Manual Review -> Final Tagging
    """

    def __init__(self, db: Session):
        self.db = db
        self.rule_engine = RuleEngine(db)

    def run(self, field_ids: list[int] | None = None, mode: str = "full") -> dict:
        """Run the tagging pipeline.
        mode: "rules_only" | "ai_only" | "full"
        Returns: {task_id, processed, classified, tiered, errors}
        """
        if field_ids:
            fields = self.db.query(Field).filter(Field.id.in_(field_ids), Field.status == "active").all()
        else:
            fields = self.db.query(Field).filter(Field.status == "active").all()

        processed = 0
        classified = 0
        tiered = 0
        errors = []

        for field in fields:
            try:
                if mode in ("rules_only", "full"):
                    result = self.rule_engine.classify_field(field)
                    if result["category_id"] or result["tier_level"]:
                        self._apply_result(field, result, "rule_engine")
                        if result["category_id"]:
                            classified += 1
                        if result["tier_level"]:
                            tiered += 1
                        processed += 1
                        continue

                if mode in ("ai_only", "full"):
                    ai_result = self._run_ai(field)
                    if ai_result and (ai_result.get("category_id") or ai_result.get("tier_level")):
                        self._apply_result(field, ai_result, "ai")
                        if ai_result.get("category_id"):
                            classified += 1
                        if ai_result.get("tier_level"):
                            tiered += 1
                        processed += 1
            except Exception as e:
                errors.append({"field_id": field.id, "field_name": field.name, "error": str(e)})

        self.db.commit()
        return {"processed": processed, "classified": classified, "tiered": tiered, "errors": errors}

    def _apply_result(self, field: Field, result: dict, method: str):
        """Apply tagging result to field and create history record."""
        now = datetime.now(timezone.utc)

        old_cat = field.classification_id
        old_tier = field.sensitivity_level
        new_cat = result.get("category_id")
        new_tier = result.get("tier_level")

        # Only create history if something changed
        if old_cat == new_cat and old_tier == new_tier:
            return

        field.classification_id = new_cat or field.classification_id
        field.sensitivity_level = new_tier or field.sensitivity_level
        field.tagging_method = method
        field.tagging_confidence = result.get("confidence", 0.0)
        field.last_tagged_at = now
        field.updated_at = now

        history = TaggingHistory(
            field_id=field.id,
            action="auto_tagged",
            old_category_id=old_cat,
            new_category_id=field.classification_id,
            old_tier_level=old_tier,
            new_tier_level=field.sensitivity_level,
            old_confidence=None,
            new_confidence=field.tagging_confidence,
            tagging_method=method,
            comment=f"Auto-tagged via {method}",
        )
        self.db.add(history)

    def _run_ai(self, field: Field) -> dict | None:
        """Run AI classification on a single field."""
        categories = (
            self.db.query(ClassificationCategory)
            .filter(ClassificationCategory.is_active == True)
            .all()
        )
        tier_rules = (
            self.db.query(TieringRule)
            .filter(TieringRule.is_active == True)
            .all()
        )

        field_data = {
            "id": field.id,
            "name": field.name,
            "data_type": field.data_type,
            "table_name": field.table_name,
            "business_domain": field.business_domain,
            "description": field.description or "",
        }
        categories_data = [
            {"id": c.id, "name": c.name, "code": c.code, "keywords": c.keywords or ""}
            for c in categories
        ]
        tier_data = [
            {"tier_level": t.tier_level, "tier_name": t.tier_name, "rule_content": t.rule_content}
            for t in tier_rules
        ]

        try:
            return classify_field_with_ai(field_data, categories_data, tier_data)
        except Exception:
            return None

    def manual_update(self, field: Field, category_id: int | None, tier_level: str | None,
                      confidence: float, operator_id: int, comment: str = "") -> Field:
        """Apply a manual tagging update."""
        old_cat = field.classification_id
        old_tier = field.sensitivity_level
        old_conf = field.tagging_confidence
        now = datetime.now(timezone.utc)

        field.classification_id = category_id if category_id is not None else field.classification_id
        field.sensitivity_level = tier_level if tier_level is not None else field.sensitivity_level
        field.tagging_method = "manual"
        field.tagging_confidence = confidence
        field.last_tagged_at = now
        field.updated_at = now

        history = TaggingHistory(
            field_id=field.id,
            action="manual_update",
            old_category_id=old_cat,
            new_category_id=field.classification_id,
            old_tier_level=old_tier,
            new_tier_level=field.sensitivity_level,
            old_confidence=old_conf,
            new_confidence=confidence,
            tagging_method="manual",
            operator_id=operator_id,
            comment=comment,
        )
        self.db.add(history)
        return field
