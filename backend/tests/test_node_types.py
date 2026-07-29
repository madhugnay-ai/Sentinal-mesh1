import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from constants.node_types import (
    APPROVAL,
    BUDGET_VALIDATION,
    INVENTORY,
    PURCHASE_ORDER,
    REQUIREMENT_VALIDATION,
    VENDOR_SELECTION,
)


def test_node_type_constants_match_expected_values() -> None:
    assert REQUIREMENT_VALIDATION == "Requirement Validation"
    assert INVENTORY == "Inventory"
    assert VENDOR_SELECTION == "Vendor Selection"
    assert BUDGET_VALIDATION == "Budget Validation"
    assert APPROVAL == "Approval"
    assert PURCHASE_ORDER == "Purchase Order"
    from constants.node_types import CONDITION

    assert CONDITION == "Condition"
