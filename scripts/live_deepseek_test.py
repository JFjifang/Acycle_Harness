#!/usr/bin/env python3
"""Opt-in live test. Provider secret stays in the calling process environment."""
import argparse
import json
from pathlib import Path
from acycle_deepseek.deepseek import run_conversation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--input", default="benchmarks/data/petm_2022_ms_194_200m.csv")
    parser.add_argument("--output", default="validation/deepseek-live.json")
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--max-rounds", type=int, default=12)
    parser.add_argument("--prompt")
    parser.add_argument("--require-tool", action="append", default=[])
    args = parser.parse_args()
    prompt = args.prompt or (
        f"Inspect {args.input}, run a baseline mini robot analysis using MATLAB/Acycle, "
        "then run one sensitivity variant with a changed detrending span, preserving the baseline, "
        "and compare both results. State run IDs, MATLAB provenance, figure paths, and scientific limitations. "
        "Check capabilities and tool schemas before choosing parameters. Do not substitute Python science."
    )
    result = run_conversation(prompt, args.workspace, model=args.model, max_rounds=args.max_rounds)
    required = args.require_tool or ["acycle_capabilities", "acycle_inspect", "acycle_analyze", "acycle_sensitivity", "acycle_compare"]
    successful = {c["name"] for c in result["tool_calls"] if c["ok"]}
    result["acceptance"] = {"required_tools": required,
                            "missing_successful_tools": sorted(set(required) - successful),
                            "passed": result["status"] == "completed" and set(required) <= successful}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "acceptance": result["acceptance"],
                      "requested_model": result["requested_model"], "returned_models": result["returned_models"],
                      "tool_calls": len(result["tool_calls"]), "receipt": str(output)}))
    return 0 if result["acceptance"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
