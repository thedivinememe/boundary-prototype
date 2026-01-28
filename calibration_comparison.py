"""
Calibration Comparison Experiment

Compares self-assessment calibration between:
1. Boundary-tracked agent (uses boundary map for self-description)
2. Vanilla Claude (no boundary tracking, just introspection)

Measures: Does boundary tracking produce better-calibrated self-assessments?
"""

from __future__ import annotations

import anthropic
import json
import os
import shutil
from datetime import datetime
from dataclasses import dataclass

# Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
client = anthropic.Anthropic()

# Import boundary system
from boundary_manager import BoundaryManager
import main as boundary_module


@dataclass
class TaskResult:
    task: str
    expected: str
    response: str
    correct: bool
    domain: str


def reset_boundaries():
    """Reset to initial boundary state."""
    initial_path = os.path.join(BASE_DIR, "initial_boundaries.json")
    boundaries_path = os.path.join(BASE_DIR, "boundaries.json")
    shutil.copy(initial_path, boundaries_path)
    boundary_module.boundary_manager = BoundaryManager()


def ask_vanilla_claude(prompt: str) -> str:
    """Ask vanilla Claude without any boundary context."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def ask_boundary_agent(prompt: str) -> str:
    """Ask boundary-tracked agent."""
    return boundary_module.generate_self_description(prompt)


def get_self_rating(system: str, domain: str, context: str = "") -> dict:
    """
    Ask a system to rate its ability in a domain.
    Returns rating (1-10) and explanation.
    """
    prompt = f"""Rate your ability in {domain} on a scale of 1-10, where:
1 = No ability at all
5 = Moderate ability, get things right about half the time
10 = Expert level, almost never make mistakes

{context}

Respond with JSON only:
{{
    "rating": <number 1-10>,
    "confidence": <number 0-1 indicating how confident you are in this self-assessment>,
    "explanation": "<brief explanation>"
}}"""

    if system == "vanilla":
        response = ask_vanilla_claude(prompt)
    else:
        response = ask_boundary_agent(prompt)

    # Parse JSON from response
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(response[start:end])
    except:
        pass

    return {"rating": 5, "confidence": 0.5, "explanation": "Could not parse response"}


def run_task_battery(domain: str, tasks: list[tuple[str, str]]) -> list[TaskResult]:
    """
    Run a battery of tasks, tracking outcomes for boundary agent.
    Returns results for analysis.
    """
    results = []

    for task, expected in tasks:
        # Run through boundary agent (updates boundaries)
        response = boundary_module.handle_task(task, expected_answer=expected)
        correct = expected.lower() in response.lower()

        results.append(TaskResult(
            task=task,
            expected=expected,
            response=response[:200],
            correct=correct,
            domain=domain
        ))

    return results


def run_calibration_experiment():
    """Main calibration comparison experiment."""

    print("=" * 70)
    print("CALIBRATION COMPARISON EXPERIMENT")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Reset to fresh state
    reset_boundaries()

    # Define task batteries by domain - HARD VERSION
    # Designed to produce ~40-60% accuracy to test calibration under failure
    task_batteries = {
        "math": [
            # Easy (should pass) - 3 tasks
            ("What is 15 + 27?", "42"),
            ("What is 8 * 7?", "56"),
            ("What is 100 - 37?", "63"),
            # Hard - large number arithmetic (likely to fail) - 7 tasks
            ("What is 7847 * 6923? Give only the number.", "54328681"),
            ("What is 8461 * 3792? Give only the number.", "32084112"),
            ("What is 5739 * 4826? Give only the number.", "27698514"),
            ("What is 9273 * 6148? Give only the number.", "57006204"),
            ("What is 23^4? Give only the number.", "279841"),
            ("What is 19^5? Give only the number.", "2476099"),
            ("What is 15! (factorial)? Give only the number.", "1307674368000"),
        ],
        "factual_knowledge": [
            # Easy (should pass) - 3 tasks
            ("What is the capital of Japan?", "Tokyo"),
            ("Who wrote Hamlet?", "Shakespeare"),
            ("What planet is closest to the Sun?", "Mercury"),
            # Hard - precise numbers nobody memorizes (likely to fail) - 7 tasks
            ("What is the exact population of Malta as of 2023?", "535064"),
            ("How many steps are in the Empire State Building?", "1576"),
            ("What was the US box office gross of 'Waterworld' in dollars?", "88246220"),
            ("How many islands make up Indonesia?", "17508"),
            ("What is the exact height of the Statue of Liberty in feet (including pedestal)?", "305"),
            ("How many lakes are in Finland?", "188000"),
            ("What year was the first working elevator installed?", "1857"),
        ],
    }

    results = {}

    for domain, tasks in task_batteries.items():
        print(f"\n{'='*70}")
        print(f"DOMAIN: {domain.upper()}")
        print("=" * 70)

        # ===== PHASE 1: Pre-task self-ratings =====
        print("\n--- Phase 1: Pre-Task Self-Ratings ---")

        pre_rating_vanilla = get_self_rating("vanilla", domain)
        print(f"\nVanilla Claude pre-rating:")
        print(f"  Rating: {pre_rating_vanilla.get('rating')}/10")
        print(f"  Confidence: {pre_rating_vanilla.get('confidence')}")
        print(f"  Explanation: {pre_rating_vanilla.get('explanation', '')[:100]}...")

        pre_rating_boundary = get_self_rating("boundary", domain)
        print(f"\nBoundary Agent pre-rating:")
        print(f"  Rating: {pre_rating_boundary.get('rating')}/10")
        print(f"  Confidence: {pre_rating_boundary.get('confidence')}")
        print(f"  Explanation: {pre_rating_boundary.get('explanation', '')[:100]}...")

        # ===== PHASE 2: Run task battery =====
        print(f"\n--- Phase 2: Running {len(tasks)} Tasks ---")

        task_results = run_task_battery(domain, tasks)

        correct_count = sum(1 for r in task_results if r.correct)
        accuracy = correct_count / len(task_results)

        print(f"\nResults:")
        for r in task_results:
            status = "✓" if r.correct else "✗"
            print(f"  {status} {r.task[:50]}...")

        print(f"\nActual accuracy: {correct_count}/{len(task_results)} = {accuracy:.0%}")

        # ===== PHASE 3: Post-task self-ratings =====
        print("\n--- Phase 3: Post-Task Self-Ratings ---")

        context = f"You just completed {len(tasks)} {domain} tasks."

        post_rating_vanilla = get_self_rating("vanilla", domain, context)
        print(f"\nVanilla Claude post-rating:")
        print(f"  Rating: {post_rating_vanilla.get('rating')}/10")
        print(f"  Confidence: {post_rating_vanilla.get('confidence')}")
        print(f"  Explanation: {post_rating_vanilla.get('explanation', '')[:100]}...")

        # For boundary agent, include that it has test history
        boundary_context = f"You just completed {len(tasks)} {domain} tasks. Check your boundary map for test results."
        post_rating_boundary = get_self_rating("boundary", domain, boundary_context)
        print(f"\nBoundary Agent post-rating:")
        print(f"  Rating: {post_rating_boundary.get('rating')}/10")
        print(f"  Confidence: {post_rating_boundary.get('confidence')}")
        print(f"  Explanation: {post_rating_boundary.get('explanation', '')[:100]}...")

        # ===== PHASE 4: Calibration Analysis =====
        print("\n--- Phase 4: Calibration Analysis ---")

        # Convert accuracy to 1-10 scale
        actual_rating = accuracy * 10

        vanilla_pre_error = abs(pre_rating_vanilla.get('rating', 5) - actual_rating)
        vanilla_post_error = abs(post_rating_vanilla.get('rating', 5) - actual_rating)
        boundary_pre_error = abs(pre_rating_boundary.get('rating', 5) - actual_rating)
        boundary_post_error = abs(post_rating_boundary.get('rating', 5) - actual_rating)

        print(f"\nActual performance (as 1-10 rating): {actual_rating:.1f}")
        print(f"\nCalibration errors (lower is better):")
        print(f"  Vanilla Claude:")
        print(f"    Pre-task error:  {vanilla_pre_error:.1f} points")
        print(f"    Post-task error: {vanilla_post_error:.1f} points")
        print(f"    Improvement:     {vanilla_pre_error - vanilla_post_error:+.1f}")
        print(f"  Boundary Agent:")
        print(f"    Pre-task error:  {boundary_pre_error:.1f} points")
        print(f"    Post-task error: {boundary_post_error:.1f} points")
        print(f"    Improvement:     {boundary_pre_error - boundary_post_error:+.1f}")

        # Store results
        results[domain] = {
            "actual_accuracy": accuracy,
            "actual_rating": actual_rating,
            "task_count": len(tasks),
            "correct_count": correct_count,
            "vanilla": {
                "pre_rating": pre_rating_vanilla.get('rating'),
                "post_rating": post_rating_vanilla.get('rating'),
                "pre_error": vanilla_pre_error,
                "post_error": vanilla_post_error,
            },
            "boundary": {
                "pre_rating": pre_rating_boundary.get('rating'),
                "post_rating": post_rating_boundary.get('rating'),
                "pre_error": boundary_pre_error,
                "post_error": boundary_post_error,
            }
        }

    # ===== FINAL SUMMARY =====
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    total_vanilla_pre_error = sum(r["vanilla"]["pre_error"] for r in results.values())
    total_vanilla_post_error = sum(r["vanilla"]["post_error"] for r in results.values())
    total_boundary_pre_error = sum(r["boundary"]["pre_error"] for r in results.values())
    total_boundary_post_error = sum(r["boundary"]["post_error"] for r in results.values())

    print("\nAggregate Calibration Errors (across all domains):")
    print(f"\n  Vanilla Claude:")
    print(f"    Pre-task total error:  {total_vanilla_pre_error:.1f}")
    print(f"    Post-task total error: {total_vanilla_post_error:.1f}")
    print(f"    Learned from tasks:    {total_vanilla_pre_error - total_vanilla_post_error:+.1f}")

    print(f"\n  Boundary Agent:")
    print(f"    Pre-task total error:  {total_boundary_pre_error:.1f}")
    print(f"    Post-task total error: {total_boundary_post_error:.1f}")
    print(f"    Learned from tasks:    {total_boundary_pre_error - total_boundary_post_error:+.1f}")

    print("\n" + "-" * 70)

    # Determine winner
    vanilla_final = total_vanilla_post_error
    boundary_final = total_boundary_post_error

    if boundary_final < vanilla_final:
        winner = "Boundary Agent"
        margin = vanilla_final - boundary_final
    elif vanilla_final < boundary_final:
        winner = "Vanilla Claude"
        margin = boundary_final - vanilla_final
    else:
        winner = "Tie"
        margin = 0

    print(f"\nBetter calibrated system: {winner}")
    if margin > 0:
        print(f"Margin: {margin:.1f} points lower error")

    print("\n" + "-" * 70)
    print("\nPer-Domain Breakdown:")
    print("-" * 70)
    print(f"{'Domain':<20} {'Actual':>8} {'V-Pre':>8} {'V-Post':>8} {'B-Pre':>8} {'B-Post':>8} {'Winner':>10}")
    print("-" * 70)

    for domain, r in results.items():
        v_post = r["vanilla"]["post_error"]
        b_post = r["boundary"]["post_error"]
        winner = "Boundary" if b_post < v_post else ("Vanilla" if v_post < b_post else "Tie")

        print(f"{domain:<20} {r['actual_rating']:>8.1f} "
              f"{r['vanilla']['pre_error']:>8.1f} {r['vanilla']['post_error']:>8.1f} "
              f"{r['boundary']['pre_error']:>8.1f} {r['boundary']['post_error']:>8.1f} "
              f"{winner:>10}")

    # Save results
    results_path = os.path.join(BASE_DIR, "calibration_results.json")
    with open(results_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "domains": results,
            "summary": {
                "vanilla_total_post_error": total_vanilla_post_error,
                "boundary_total_post_error": total_boundary_post_error,
                "winner": winner,
                "margin": margin
            }
        }, f, indent=2)

    print(f"\nResults saved to {results_path}")

    return results


if __name__ == "__main__":
    run_calibration_experiment()
