"""6단계: cases.json의 사건들을 계산해 expected와 비교하고 PASS/FAIL 리포트를 낸다."""

import json

from calculator import calculate
from core import load_rules

KEYS = ("tax_base", "income_tax", "local_tax", "total_tax")


def load_cases(path="cases.json"):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)["cases"]
    except FileNotFoundError:
        print(f"오류: {path} 파일을 찾을 수 없습니다.")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"오류: {path} 형식이 올바르지 않습니다. ({e})")
    return None


def compare(case, rules):
    """사건 1건을 계산해 expected와 비교한다. 반환: (PASS 여부, 실제 요약, 사유)"""
    exp = case["expected"]
    inp = dict(case["input"])
    available = str(inp.pop("basic_deduction_used", "")).strip() not in ("예", "y", "yes", "true")
    try:
        result = calculate(inp, rules, basic_deduction_available=available)
    except ValueError as e:
        if exp.get("error"):
            return True, f"입력 오류로 처리됨: {e}", ""
        return False, f"입력 오류: {e}", "예상과 달리 입력 오류가 발생했습니다."

    if exp.get("error"):
        return False, result["status"], "입력 오류가 나와야 하는데 계산되었습니다."
    if result["status"] != exp["status"]:
        return False, result["status"], f"판정 불일치 (예상 {exp['status']})"
    if exp["status"] == "CONSULT":
        return True, "상담 필요", ""
    got = {"tax_base": result["base"]["tax_base"], "income_tax": result["income_tax"],
           "local_tax": result["local_tax"], "total_tax": result["total_tax"]}
    diffs = [f"{k}: 계산 {got[k]:,} / 예상 {exp[k]:,}" for k in KEYS if got[k] != exp[k]]
    return (not diffs), f"합계 {got['total_tax']:,}원", "; ".join(diffs)


def run_all(path="cases.json"):
    """전체 사건을 실행하고 결과를 출력한다. 반환: (총, 통과, 실패 목록)"""
    cases = load_cases(path)
    if cases is None:
        return 0, 0, []
    rules = load_rules()
    failed = []
    for c in cases:
        ok, summary, why = compare(c, rules)
        print(f"[{'PASS' if ok else 'FAIL'}] {c['id']} {c['title']}")
        print(f"       {summary}" + (f" | {why}" if why else ""))
        if not ok:
            failed.append((c["id"], why))
    total = len(cases)
    print(f"\n총 테스트: {total}개 / 통과: {total - len(failed)}개 / 실패: {len(failed)}개")
    for cid, why in failed:
        print(f"- {cid}: {why}")
    return total, total - len(failed), failed


if __name__ == "__main__":
    run_all()
