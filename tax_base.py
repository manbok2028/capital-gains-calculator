"""양도소득세 계산기 - 4단계: 양도차익 -> 장기보유특별공제 -> 기본공제 -> 과세표준

계산 단계마다 원 미만은 절사한다. (절사 시점은 세무사 확인 필요: floor_won 한 곳에서 관리)
"""

from fractions import Fraction

from exemption import format_won


def floor_won(x):
    """원 미만 절사 (0 이상 값만 다룬다)."""
    return int(x) if x > 0 else 0


def long_term_rate(holding, residence, one_house, rules):
    """장기보유특별공제율을 구한다. 반환: (공제율 %, 'table1'|'table2'|'none', 설명)

    one_house: 1세대 1주택 비과세 요건을 충족한 주택인지 (표2 적용 후보)
    표2: 보유 3년 이상 + 거주 2년 이상이면 보유 연 4%(최대 40%) + 거주 연 4%(최대 40%)
    표1: 그 밖에는 보유 3년 이상부터 연 2%(최대 30%)
    """
    ltd = rules["long_term_deduction"]
    t2, t1 = ltd["table2_one_house"], ltd["table1_general"]

    if one_house and holding >= t2["min_holding_years"] and residence >= t2["min_residence_years"]:
        hold_pct = min(t2["holding_max_pct"], t2["holding_per_year_pct"] * holding)
        res_pct = min(t2["residence_max_pct"], t2["residence_per_year_pct"] * residence)
        return (hold_pct + res_pct, "table2",
                f"1세대 1주택 공제표 적용: 보유 {holding}년 {hold_pct}% + 거주 {residence}년 {res_pct}%")

    if holding >= t1["min_holding_years"]:
        pct = min(t1["max_pct"], t1["per_year_pct"] * holding)
        return pct, "table1", f"일반 공제표 적용: 보유 {holding}년 x 연 {t1['per_year_pct']}%"

    return 0, "none", f"보유기간 {holding}년으로 장기보유특별공제 대상(3년 이상)이 아닙니다."


def _zero(steps, note):
    steps.update({"taxable_gain": 0, "ltd_table": "none", "ltd_rate_pct": 0, "ltd_amount": 0,
                  "income_amount": 0, "basic_deduction": 0, "tax_base": 0})
    steps["notes"].append(note)
    return steps


def calc_tax_base(case, periods, exemption, rules, basic_deduction_available=True):
    """과세표준까지 계산한다. 반환: 단계별 금액과 설명이 담긴 dict.

    exemption: exemption.judge_exemption() 결과. '상담 필요'는 계산하지 않는다.
    basic_deduction_available: 올해 다른 양도소득에서 기본공제(연 250만원)를 이미 쓰지 않았는지.
    """
    if exemption["status"] == "CONSULT":
        raise ValueError("상담이 필요한 사례는 자동 계산하지 않습니다.")

    gain = case["transfer_price"] - case["acquisition_price"] - case["expenses"]
    steps = {"gain": gain, "notes": []}

    if exemption["status"] == "EXEMPT":
        return _zero(steps, "1세대 1주택 비과세로 과세되는 양도차익이 없습니다.")
    if gain <= 0:
        return _zero(steps, "양도차익이 없거나 양도차손이라 납부할 세금이 없습니다.")

    # 1) 과세 대상 양도차익: 고가주택은 12억 초과분 비율만
    if exemption["status"] == "HIGH_VALUE_PARTIAL":
        taxable_gain = floor_won(gain * exemption["taxable_ratio"])
        steps["notes"].append(f"고가주택 안분: 양도차익 {format_won(gain)} x {exemption['taxable_ratio']} "
                              f"= {format_won(taxable_gain)}")
    else:
        taxable_gain = gain

    # 2) 장기보유특별공제
    rate, table, why = long_term_rate(periods["holding_years"], periods["residence_years"],
                                      exemption["status"] == "HIGH_VALUE_PARTIAL", rules)
    ltd_amount = floor_won(taxable_gain * rate / 100)
    steps["notes"].append(why + f" -> 공제율 {rate}%")

    # 3) 양도소득금액, 기본공제, 과세표준
    income = taxable_gain - ltd_amount
    basic = min(rules["basic_deduction"], income) if basic_deduction_available else 0
    steps.update({"taxable_gain": taxable_gain, "ltd_table": table, "ltd_rate_pct": rate,
                  "ltd_amount": ltd_amount, "income_amount": income,
                  "basic_deduction": basic, "tax_base": income - basic})
    if not basic_deduction_available:
        steps["notes"].append("올해 이미 기본공제를 받아 이번 양도에는 적용하지 않았습니다.")
    return steps


def describe_base(s):
    """과세표준 계산 과정을 사람이 읽는 표로 만든다."""
    rows = [
        ("양도차익", s["gain"]),
        ("과세 대상 양도차익", s["taxable_gain"]),
        (f"장기보유특별공제 ({s['ltd_rate_pct']}%)", -s["ltd_amount"]),
        ("양도소득금액", s["income_amount"]),
        ("기본공제", -s["basic_deduction"]),
        ("과세표준", s["tax_base"]),
    ]
    lines = [f"{name:<22}{format_won(abs(v)) if v >= 0 else '-' + format_won(abs(v)):>20}" for name, v in rows]
    lines += [f"* {n}" for n in s["notes"]]
    return "\n".join(lines)


if __name__ == "__main__":
    from core import load_rules
    from exemption import judge_exemption, parse_scope
    from inputs import normalize_case, compute_periods

    rules = load_rules()
    raw = {
        "acquisition_date": "2018-05-10", "transfer_date": "2026-11-20",
        "acquisition_price": "5억", "transfer_price": "15억",
        "residence_start": "2018-05-10", "residence_end": "2026-11-20",
    }
    case = normalize_case(raw)
    periods = compute_periods(case)
    ex = judge_exemption(case, periods, parse_scope(raw), rules)
    print(f"[비과세 판정] {ex['label']}\n")
    print(describe_base(calc_tax_base(case, periods, ex, rules)))
