"""양도소득세 계산기 - 일시적 2주택 비과세 특례 판정 (소득세법 시행령 제155조 제1항)

종전주택을 취득하고 1년 이상 지난 뒤 신규주택을 취득해 일시적으로 2주택이 된 1세대가
신규주택 취득일부터 3년 이내에 종전주택을 양도하면 1세대 1주택으로 본다.
조정대상지역의 종전주택을 가진 채 조정대상지역의 신규주택을 취득한 경우(2026.8.4. 이후 취득,
2026.10.1. 이후 양도)는 기한이 2년이다. (대통령령 제36737호)
"""

from datetime import timedelta

from inputs import add_years, parse_date


def _flag(value):
    if isinstance(value, str):
        return value.strip().lower() in ("y", "yes", "예", "네", "true", "1")
    return bool(value)


def _optional_date(value):
    return None if value in (None, "") else parse_date(value)


def parse_two_house_inputs(raw):
    """2주택 판정에 필요한 입력을 검증한다. 오류는 ValueError."""
    if raw.get("new_house_acquisition_date") in (None, ""):
        raise ValueError("세대 보유 주택이 2채이면 신규주택 취득일(new_house_acquisition_date)이 필요합니다.")
    try:
        before = int(str(raw.get("house_count_before_new", 1)).strip())
    except ValueError:
        raise ValueError("신규주택 취득 직전 세대 보유 주택 수는 숫자로 입력하세요.")
    return {
        "new_date": parse_date(raw["new_house_acquisition_date"]),
        "contract_date": _optional_date(raw.get("new_house_contract_date")),
        "before_count": before,
        "old_reg": _flag(raw.get("old_house_regulated_at_new_acquisition", False)),
        "new_reg": _flag(raw.get("new_house_regulated_at_acquisition", False)),
        "designation_date": _optional_date(raw.get("new_area_designation_date")),
    }


def deadline_years(t, transfer_date, rules):
    """종전주택 양도기한(년)과 그 이유를 돌려준다. 2년 규정은 아래 4가지를 모두 만족할 때만."""
    cfg = rules["temporary_two_house"]
    default, short = cfg["default_deadline_years"], cfg["regulated_deadline_years"]
    new_from = parse_date(cfg["regulated_rule_new_acquisition_on_or_after"])
    transfer_from = parse_date(cfg["regulated_rule_transfer_on_or_after"])

    if not (t["old_reg"] and t["new_reg"]):
        return default, "종전주택과 신규주택이 모두 조정대상지역에 있는 경우가 아니라 3년"
    # 계약금을 먼저 지급했다면 그 날을 신규주택 취득 시점으로 본다 (부칙 제2조)
    basis = t["new_date"] if t["contract_date"] is None else min(t["new_date"], t["contract_date"])
    if basis < new_from:
        return default, f"신규주택 취득(또는 계약금 지급)이 {new_from.isoformat()} 전이라 종전 규정 3년"
    if transfer_date < transfer_from:
        return default, f"종전주택 양도일이 시행일({transfer_from.isoformat()}) 전이라 종전 규정 3년"
    if t["designation_date"] is not None and basis <= t["designation_date"]:
        return default, "조정대상지역 공고일 이전에 신규주택을 취득(또는 계약금 지급)해 3년"
    return short, "조정대상지역 내 이동이라 2년"


def check_temporary_two_house(case, raw, rules):
    """일시적 2주택 특례 요건을 확인한다.

    case: inputs.normalize_case() 결과(종전주택 기준). 반환: qualifies(bool), reasons(문장 목록),
    deadline_years, deadline(date). 자료 모순(날짜 순서 등)은 ValueError.
    """
    t = parse_two_house_inputs(raw)
    old_acq, transfer = case["acquisition_date"], case["transfer_date"]
    if t["new_date"] < old_acq:
        raise ValueError("신규주택 취득일이 종전주택 취득일보다 앞섭니다.")
    if t["new_date"] > transfer:
        raise ValueError("신규주택 취득일이 양도일보다 늦습니다. (양도일 현재 2주택이어야 합니다.)")
    if t["contract_date"] is not None and t["contract_date"] > t["new_date"]:
        raise ValueError("계약금 지급일이 신규주택 취득일보다 늦습니다.")

    fails = []
    if t["before_count"] != 1:
        fails.append(f"신규주택을 취득하기 직전 세대 보유 주택이 {t['before_count']}채입니다. "
                     "1주택 상태에서 신규주택을 취득한 경우에만 특례가 적용됩니다.")

    cfg = rules["temporary_two_house"]
    earliest = add_years(old_acq, cfg["min_years_after_old_acquisition"]) + timedelta(days=1)
    if t["new_date"] < earliest:
        fails.append(f"종전주택 취득일({old_acq.isoformat()})부터 1년이 지난 후({earliest.isoformat()} 이후)에 "
                     f"신규주택을 취득해야 하는데 신규주택 취득일은 {t['new_date'].isoformat()}입니다.")

    years, why = deadline_years(t, transfer, rules)
    deadline = add_years(t["new_date"], years)
    if transfer > deadline:
        fails.append(f"신규주택 취득일({t['new_date'].isoformat()})부터 {years}년 이내({deadline.isoformat()}까지)에 "
                     f"종전주택을 양도해야 하는데 양도일은 {transfer.isoformat()}입니다. ({why})")

    reasons = fails or [
        f"종전주택 취득일({old_acq.isoformat()}) 후 1년이 지난 {earliest.isoformat()} 이후"
        f"({t['new_date'].isoformat()})에 신규주택을 취득했습니다.",
        f"신규주택 취득일부터 {years}년 이내({deadline.isoformat()}까지)에 종전주택을 양도했습니다. ({why})",
        "일시적 2주택 특례에 따라 종전주택을 1세대 1주택으로 보아 판정합니다.",
    ]
    return {"qualifies": not fails, "reasons": reasons, "deadline_years": years, "deadline": deadline}
