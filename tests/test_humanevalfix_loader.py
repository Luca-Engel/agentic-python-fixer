# test_sampling.py
import math
import pytest
from collections import Counter

from eval.humanevalfix_loader import stratified_sample


def make_tasks(per_class_counts):
    """
    Build a simple list[dict] dataset where each dict has:
      - uid: globally unique id for duplicate checks
      - bug_type: class label
    per_class_counts: dict[str, int] mapping bug_type -> size
    """
    tasks = []
    uid = 0
    for bug_type, n in per_class_counts.items():
        for i in range(n):
            tasks.append(
                {
                    "uid": f"{bug_type}-{i}",
                    "bug_type": bug_type,
                    # extra keys the real dataset has are unused by stratified_sample and left out here
                }
            )
            uid += 1
    return tasks


def count_by_type(sampled):
    return Counter(t["bug_type"] for t in sampled)


def uids(sampled):
    return {t["uid"] for t in sampled}


def test_invalid_percent_raises():
    ds = make_tasks({"A": 3})
    with pytest.raises(ValueError):
        stratified_sample(ds, percent=-0.1)
    with pytest.raises(ValueError):
        stratified_sample(ds, percent=1.1)


@pytest.mark.parametrize(
    "sizes,percent,min_per_class,expected",
    [
        # percent drives selection (ceil used), min_per_class low so it doesn't intervene
        ({"A": 10, "B": 7, "C": 4}, 0.2, 1, {"A": 2, "B": 2, "C": 1}),
        ({"A": 5, "B": 5}, 0.4, 1, {"A": 2, "B": 2}),  # ceil(2.0)=2
        ({"A": 3, "B": 8}, 0.125, 0, {"A": 1, "B": 1}),  # ceil(0.375)=1, ceil(1.0)=1
        # min_per_class enforces floor when percent too small
        ({"A": 10, "B": 3}, 0.0, 2, {"A": 2, "B": 2}),
        # cap by available items: cannot exceed class size
        ({"A": 3, "B": 2}, 0.9, 5, {"A": 3, "B": 2}),
        # percent=1.0 --> select all
        ({"A": 4, "B": 6}, 1.0, 1, {"A": 4, "B": 6}),
    ],
)
def test_per_class_counts_respected(sizes, percent, min_per_class, expected):
    ds = make_tasks(sizes)
    sampled = stratified_sample(ds, percent=percent, min_per_class=min_per_class, seed=0)
    got = count_by_type(sampled)
    assert got == Counter(expected)


def test_min_per_class_enforced_but_not_exceeding_available():
    ds = make_tasks({"A": 3, "B": 10})
    sampled = stratified_sample(ds, percent=0.1, min_per_class=5, seed=123)
    # For A: only 3 exist -> we must take all 3, not 5.
    # For B: ceil(10*0.1)=1, but min_per_class=5 -> take 5.
    got = count_by_type(sampled)
    assert got["A"] == 3
    assert got["B"] == 5
    # Total is sum of those
    assert len(sampled) == 8


def test_percentage_matches_ceil_without_min_override():
    sizes = {"A": 9, "B": 11, "C": 1}
    percent = 0.33
    ds = make_tasks(sizes)
    sampled = stratified_sample(ds, percent=percent, min_per_class=0, seed=42)
    # Expected per class is ceil(n * p)
    expected = {k: min(math.ceil(n * percent), n) for k, n in sizes.items()}
    assert count_by_type(sampled) == Counter(expected)


def test_no_duplicates_and_all_from_input():
    sizes = {"A": 30, "B": 30}
    ds = make_tasks(sizes)
    sampled = stratified_sample(ds, percent=0.5, min_per_class=1, seed=7)
    ids = uids(sampled)
    # uniqueness
    assert len(ids) == len(sampled)
    # all sampled are from ds
    assert ids.issubset(uids(ds))
    # counts per class as expected
    assert count_by_type(sampled) == Counter({"A": 15, "B": 15})


def test_deterministic_with_same_seed_and_varies_with_different_seed():
    ds = make_tasks({"A": 50, "B": 21})
    s1 = stratified_sample(ds, percent=0.3, min_per_class=5, seed=123)
    s2 = stratified_sample(ds, percent=0.3, min_per_class=5, seed=123)
    s3 = stratified_sample(ds, percent=0.3, min_per_class=5, seed=124)
    # same seed -> identical order & content
    assert [t["uid"] for t in s1] == [t["uid"] for t in s2]
    # different seed -> usually different sample (allow equality in rare case but it's unlikely)
    assert [t["uid"] for t in s1] != [t["uid"] for t in s3] or len(s1) in (0, 1)


def test_empty_dataset_returns_empty():
    ds = []
    sampled = stratified_sample(ds, percent=0.5, min_per_class=2, seed=42)
    assert sampled == []


def test_handles_class_with_zero_items_gracefully():
    # Although our builder doesn't make zero-sized classes, simulate by not creating that class at all.
    ds = make_tasks({"A": 5})
    # Presence of an absent/zero class shouldn't affect result
    sampled = stratified_sample(ds, percent=0.4, min_per_class=2, seed=0)
    assert count_by_type(sampled) == Counter({"A": 2})


@pytest.mark.parametrize(
    "sizes,percent,min_per_class",
    [
        ({"A": 1}, 0.0, 1),  # edge: exactly min but also percent=0
        ({"A": 2}, 0.5, 1),  # edge: ceil boundary
        ({"A": 100}, 0.01, 2),  # ceil(1) vs min=2
    ],
)
def test_boundaries_and_rounding(sizes, percent, min_per_class):
    ds = make_tasks(sizes)
    sampled = stratified_sample(ds, percent=percent, min_per_class=min_per_class, seed=9)
    n = sizes["A"]
    expected = min(max(min_per_class, math.ceil(n * percent)), n)
    assert len(sampled) == expected
    assert all(t["bug_type"] == "A" for t in sampled)
