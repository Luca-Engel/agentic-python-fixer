def pass_at_1(results):
    """
    Compute pass@1 score from the list of results.
    Each result is a dict with at least a "status" key ("pass" or "fail").
    Returns (pass_at_1_score, nb_passed, nb_total)
    """
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    return passed / total if total else 0.0, passed, total
