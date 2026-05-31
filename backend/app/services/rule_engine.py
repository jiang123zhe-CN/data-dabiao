import json
import re

from sqlalchemy.orm import Session

from app.models.field import Field
from app.models.standard import ClassificationCategory, TieringRule


class RuleEngine:
    """Deterministic rule-based classification and tiering engine."""

    def __init__(self, db: Session):
        self.db = db
        self.tier_rules = (
            db.query(TieringRule)
            .filter(TieringRule.is_active == True)
            .order_by(TieringRule.priority.desc())
            .all()
        )
        self.categories = (
            db.query(ClassificationCategory)
            .filter(ClassificationCategory.is_active == True)
            .all()
        )

    def classify_field(self, field: Field) -> dict:
        """Run classification + tiering on a single field.
        Returns: {category_id, tier_level, confidence, matched_rules[], method}
        """
        category_id, cat_conf = self._match_category(field)
        tier_level, tier_conf, matched_rules = self._match_tier(field)

        if category_id and tier_level:
            method = "rule_engine"
            confidence = round((cat_conf + tier_conf) / 2, 2)
        elif category_id:
            method = "rule_engine"
            confidence = cat_conf
        elif tier_level:
            method = "rule_engine"
            confidence = tier_conf
        else:
            method = "rule_engine"
            confidence = 0.0

        return {
            "category_id": category_id,
            "tier_level": tier_level,
            "confidence": confidence,
            "matched_rules": matched_rules,
            "method": method,
        }

    def batch_classify(self, field_ids: list[int]) -> list[dict]:
        """Batch classify multiple fields."""
        results = []
        fields = (
            self.db.query(Field)
            .filter(Field.id.in_(field_ids), Field.status == "active")
            .all()
        )
        for field in fields:
            result = self.classify_field(field)
            result["field_id"] = field.id
            results.append(result)
        return results

    def classify_all_active(self) -> list[dict]:
        """Classify all active, unclassified fields."""
        fields = (
            self.db.query(Field)
            .filter(Field.status == "active")
            .all()
        )
        results = []
        for field in fields:
            result = self.classify_field(field)
            result["field_id"] = field.id
            results.append(result)
        return results

    # ── Private helpers ──

    def _match_category(self, field: Field) -> tuple[int | None, float]:
        """Match field to a classification category by keyword overlap."""
        best_id, best_score = None, 0.0
        field_text = self._field_text(field)

        for cat in self.categories:
            if not cat.keywords:
                continue
            keywords = [k.strip() for k in cat.keywords.split(",") if k.strip()]
            matches = sum(1 for kw in keywords if kw in field_text)
            if matches > 0:
                score = matches / len(keywords)
                # Bonus if business_domain overlaps with category name or code
                if field.business_domain:
                    domain_words = set(field.business_domain.replace("域", ""))
                    cat_words = set(cat.name.replace("数据", ""))
                    if domain_words & cat_words:
                        score += 0.3
                score = min(score, 1.0)
                if score > best_score:
                    best_score = score
                    best_id = cat.id

        return (best_id, round(best_score, 2)) if best_id else (None, 0.0)

    def _match_tier(self, field: Field) -> tuple[str | None, float, list[int]]:
        """Match field to a tier level using tiering rules."""
        field_text = self._field_text(field)
        matched_rule_ids = []

        for rule in self.tier_rules:
            try:
                content = json.loads(rule.rule_content)
            except (json.JSONDecodeError, TypeError):
                continue

            # Check metadata rules first
            meta = content.get("metadata_rules", {})
            if meta.get("sensitivity_level") and field.sensitivity_level == meta["sensitivity_level"]:
                return (rule.tier_level, 0.9, [rule.id])

            # Check keywords
            keywords = content.get("keywords", [])
            kw_matches = sum(1 for kw in keywords if kw.lower() in field_text.lower())
            if kw_matches >= 1:
                conf = 0.6 + kw_matches * 0.15
                return (rule.tier_level, min(conf, 1.0), [rule.id])

            # Check regex patterns
            patterns = content.get("patterns", [])
            for pattern in patterns:
                try:
                    if re.search(pattern, field_text):
                        matched_rule_ids.append(rule.id)
                        return (rule.tier_level, 0.85, [rule.id])
                except re.error:
                    continue

        return (None, 0.0, [])

    @staticmethod
    def _field_text(field: Field) -> str:
        """Combine all searchable text from a field."""
        parts = [
            field.name or "",
            field.english_name or "",
            field.description or "",
            field.business_rules or "",
            field.table_name or "",
            field.business_domain or "",
        ]
        return " ".join(parts)
