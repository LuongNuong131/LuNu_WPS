from __future__ import annotations

from collections import defaultdict

from app.document_ai.contracts import DocumentFact, GraphEdge, TruthStatus
from app.document_ai.models import CanonicalDocument


def build_truth_model(document: CanonicalDocument) -> None:
    """Build auditable facts and minimal graph links without inventing values."""
    facts: list[DocumentFact] = []
    by_name: dict[str, list[DocumentFact]] = defaultdict(list)
    for index, entity in enumerate(document.entities, start=1):
        evidence = [item.to_dict() for item in entity.evidence]
        confidence = entity.confidence.value if entity.confidence else 0.0
        status = TruthStatus.EXTRACTED if entity.normalized_value == entity.raw_value else TruthStatus.NORMALIZED
        fact = DocumentFact(
            fact_id=f"fact-{index}",
            name=entity.entity_type,
            raw_value=entity.raw_value,
            normalized_value=entity.normalized_value,
            status=status,
            confidence=confidence,
            evidence=evidence,
            explanation=["matched deterministic semantic pattern", "retains source evidence"],
        )
        facts.append(fact)
        by_name[entity.entity_type].append(fact)

    edges: list[GraphEdge] = []
    invoice_numbers = by_name.get("INVOICE_NUMBER", [])
    money = by_name.get("MONEY", [])
    for invoice in invoice_numbers:
        for amount in money:
            edges.append(GraphEdge(invoice.fact_id, "has_amount", amount.fact_id, min(invoice.confidence, amount.confidence), [*invoice.evidence, *amount.evidence]))
    document.facts = facts
    document.graph_edges = edges
