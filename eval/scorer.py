def pass_at_1(results):
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    return passed / total if total else 0.0
