"""양도소득세 계산기 - 동거봉양 합가 / 혼인 합가 비과세 특례 판정 (소득세법 시행령 제155조 제4항, 제5항)

- 동거봉양 합가: 1주택을 보유한 1세대가 1주택을 보유한 60세 이상 직계존속(배우자의 직계존속 포함)을
  동거봉양하려고 세대를 합쳐 2주택이 된 경우, 합친 날부터 10년 이내에 먼저 양도하는 주택은 1세대 1주택으로 본다.
- 혼인 합가: 1주택 보유자가 1주택 보유자와 혼인해 2주택이 된 경우, 혼인한 날부터 10년 이내에 먼저 양도하는
  주택은 1세대 1주택으로 본다. (10년은 2024.11.12. 이후 양도분부터, 그 전에는 5년)
1차 구현은 2024.11.12. 이후 양도분만 자동으로 판정하고, 그 전 양도분은 상담으로 안내한다.
"""

from inputs import add_years, parse_date

REASON_TITLES = {
    "temporary": "일시적 2주택 특례",
    "parent_care": "동거봉양 합가 특례",
    "marriage": "혼인 합가 특례",
}

_REASON_WORDS = {
    "temporary": "temporary", "신규": "temporary", "신규주택": "temporary", "일시적": "temporary",
    "parent_care": "parent_care", "동거봉양": "parent_care", "동거봉양합가": "parent_care",
    "marriage": "marriage", "혼인": "marriage", "혼인합가": "marriage",
}


def _flag(value):
    if isinstance(value, str):
        return value.strip().lower() in ("y", "yes", "예", "네", "true", "1")
    return bool(value)


def parse_two_house_reason(raw):
    """2주택이 된 이유를 표준값(temporary / parent_care / marriage)으로 바꾼다. 생략하면 신규주택."""
    word = str(raw.get("two_house_reason", "temporary")).strip().lower().replace(" ", "")
    if word in _REASON_WORDS:
        return _REASON_WORDS[word]
    raise ValueError("2주택이 된 이유는 신규주택, 동거봉양, 혼인 중에서 입력하세요.")


def check_merged_household(case, raw, rules, reason):
    """합가 특례 요건을 확인한다. 반환: qualifies(bool), reasons(문장 목록), deadline(date).

    case: inputs.normalize_case() 결과(양도하는 주택 기준). 자료 모순(날짜 순서 등)은 ValueError.
    입력 누락은 요건 미충족으로 본다(안전한 쪽).
    """
    cfg = rules["merged_household"]
    if raw.get("merge_date") in (None, ""):
        raise ValueError("합가일(혼인이면 혼인일)(merge_date)이 필요합니다.")
    merge = parse_date(raw["merge_date"])
    acq, transfer = case["acquisition_date"], case["transfer_date"]
    if merge > transfer:
        raise ValueError("합가일(혼인일)이 양도일보다 늦습니다.")

    label = "합가일" if reason == "parent_care" else "혼인일"
    fails = []

    supported_from = parse_date(cfg["supported_transfer_from"])
    if transfer < supported_from:
        fails.append(f"양도일이 {supported_from.isoformat()} 전이라 당시 시행령(기한 5년 등)을 따로 확인해야 합니다.")
    if acq > merge:
        fails.append(f"양도하는 주택을 {label}({merge.isoformat()}) 이후({acq.isoformat()})에 취득했습니다. "
                     f"{label} 당시 이미 보유한 주택이어야 합니다.")
    if not _flag(raw.get("one_house_each_before_merge", False)):
        fails.append(f"{label} 직전 양쪽 세대가 각각 1주택씩, 합쳐서 2주택이었다는 확인이 없습니다. "
                     "한쪽이 2주택 이상이면 특례를 적용받을 수 없습니다.")
    if reason == "parent_care":
        if not _flag(raw.get("parent_qualified", False)):
            fails.append(f"합가 당시 {cfg['parent_min_age']}세 이상(또는 법령이 정한 요건에 해당하는) 직계존속이 있었다는 확인이 없습니다.")
        if not _flag(raw.get("was_separate_household", False)):
            fails.append("합가 전에 실제로 별도 세대였다는 확인이 없습니다. (주민등록뿐 아니라 실제 생계 기준의 사실판단)")

    deadline = add_years(merge, cfg["years"])
    if transfer > deadline:
        fails.append(f"{label}({merge.isoformat()})부터 {cfg['years']}년 이내({deadline.isoformat()}까지)에 "
                     f"먼저 양도해야 하는데 양도일은 {transfer.isoformat()}입니다.")

    reasons = fails or [
        f"{label}({merge.isoformat()})부터 {cfg['years']}년 이내({deadline.isoformat()}까지)에 먼저 양도하는 주택입니다.",
        "양쪽 세대가 각각 1주택씩 보유하다가 합쳐 2주택이 된 경우로 확인되었습니다.",
        f"{REASON_TITLES[reason]}에 따라 양도하는 주택을 1세대 1주택으로 보아 판정합니다.",
    ]
    return {"qualifies": not fails, "reasons": reasons, "deadline": deadline}
