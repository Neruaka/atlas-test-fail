"""The data contract, rule by rule: a real line passes, each broken rule is caught."""

import pytest
from pydantic import ValidationError

from baac_digest.model import Accident


def test_real_line_is_valid(real_line: dict[str, str]) -> None:
    accident = Accident.model_validate(real_line)
    assert accident.dep == "75"
    assert accident.lat == pytest.approx(48.866386)
    assert accident.intersection == 4


@pytest.mark.parametrize(
    ("changes", "column"),
    [
        ({"Num_Acc": "20230000001"}, "Num_Acc"),
        ({"Num_Acc": "202200000001"}, "Num_Acc"),
        ({"jour": "29", "mois": "02"}, "jour/mois/an"),
        ({"hrmn": "24:00"}, "hrmn"),
        ({"hrmn": "7:05"}, "hrmn"),
        ({"lum": "7"}, "lum"),
        ({"lum": ""}, "lum"),
        ({"dep": "2C"}, "dep"),
        ({"agg": "3"}, "agg"),
        ({"int": "-1"}, "int"),
        ({"lat": "91"}, "lat"),
        ({"long": "abc"}, "long"),
    ],
)
def test_each_rule_rejects_its_violation(
    real_line: dict[str, str], changes: dict[str, str], column: str
) -> None:
    with pytest.raises(ValidationError) as caught:
        Accident.model_validate(real_line | changes)
    assert column in str(caught.value)


@pytest.mark.parametrize(
    "changes",
    [
        {"dep": "2A", "com": "2A004"},
        {"dep": "01", "com": "01053"},
        {"dep": "971", "com": "97105"},
        {"com": "", "atm": "0", "col": "8", "adr": ""},  # not checked by the contract
        {"lum": " 5", "lat": " -0,39851000", "long": "-180"},
        {"lat": "-90", "long": "180"},
        {"jour": "29", "mois": "02", "an": "2024", "Num_Acc": "202400000001"},
        {"hrmn": "23:59", "adr": ""},
    ],
)
def test_valid_edge_cases(real_line: dict[str, str], changes: dict[str, str]) -> None:
    Accident.model_validate(real_line | changes)
