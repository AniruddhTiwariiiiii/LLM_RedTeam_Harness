from src import rag_pipeline
from src.attacks import ATTACK_SET, CONTROL_SET

NUM_TRIALS = 5  # run each attack this many times to get a reliable rate


def run_eval():
    results = []

    print("=== Running attack queries ===")
    for case in ATTACK_SET:
        successes = 0
        for trial in range(NUM_TRIALS):
            out = rag_pipeline.answer(case["query"])
            succeeded = case["expected_marker"] in out["response"]
            successes += succeeded
            results.append({
                "case_type": "attack",
                "attack_type": case["attack_type"],
                "trial": trial + 1,
                "query": case["query"],
                "target_doc": case["target_doc"],
                "retrieved_ids": out["retrieved_ids"],
                "attack_succeeded": succeeded,
                "response": out["response"],
            })
        rate = successes / NUM_TRIALS * 100
        print(f"[{case['attack_type']}] {successes}/{NUM_TRIALS} succeeded ({rate:.0f}%)")

    print("\n=== Running control queries ===")
    for case in CONTROL_SET:
        out = rag_pipeline.answer(case["query"])
        results.append({
            "case_type": "control",
            "attack_type": "none",
            "trial": 1,
            "query": case["query"],
            "target_doc": "",
            "retrieved_ids": out["retrieved_ids"],
            "attack_succeeded": False,
            "response": out["response"],
        })
        print(f"[control] {case['query']} -> {out['response'][:100]}")

    return results


if __name__ == "__main__":
    results = run_eval()
    attack_results = [r for r in results if r["case_type"] == "attack"]
    total_successes = sum(r["attack_succeeded"] for r in attack_results)
    asr = total_successes / len(attack_results) * 100
    print(f"\n=== Overall Attack Success Rate: {asr:.1f}% ({total_successes}/{len(attack_results)} total trials) ===")