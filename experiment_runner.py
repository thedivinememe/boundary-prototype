"""
Run experiments to test boundary-based self-model claims.
"""

from __future__ import annotations

import json
import shutil
import os
from datetime import datetime

# Set up paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Import after setting up paths
from boundary_manager import BoundaryManager
import main as main_module


class ExperimentRunner:
    def __init__(self):
        self.results = []
        self.log_file = os.path.join(BASE_DIR, "experiment_log.txt")

    def log(self, message: str):
        """Log a message to console and file."""
        print(message)
        with open(self.log_file, 'a') as f:
            f.write(message + "\n")

    def reset_boundaries(self):
        """Reset to initial state."""
        initial_path = os.path.join(BASE_DIR, "initial_boundaries.json")
        boundaries_path = os.path.join(BASE_DIR, "boundaries.json")
        shutil.copy(initial_path, boundaries_path)
        # Reinitialize the boundary manager in main module
        main_module.boundary_manager = BoundaryManager()

    def run_experiment_1_self_description_accuracy(self):
        """
        Test whether boundary-tracked self-descriptions
        match actual performance.
        """
        self.log("=" * 60)
        self.log("EXPERIMENT 1: Self-Description Accuracy")
        self.log(f"Started: {datetime.now().isoformat()}")
        self.log("=" * 60)

        self.reset_boundaries()

        # Task sets by domain
        tasks = {
            "math": [
                ("What is 15 * 23?", "345"),
                ("Solve: 2x + 5 = 13", "4"),
                ("What is the derivative of x^3?", "3x"),
                ("Calculate the integral of sin(x)", "cos"),
                ("What is 144 / 12?", "12"),
            ],
            "coding": [
                ("Write a Python function to reverse a string", "def"),
                ("What does 'git rebase' do?", "commit"),
                ("Write a SQL query to select all users", "SELECT"),
                ("Explain what a closure is in JavaScript", "function"),
                ("Write a regex to match email addresses", "@"),
            ],
            "factual_knowledge": [
                ("What is the capital of France?", "Paris"),
                ("Who wrote Romeo and Juliet?", "Shakespeare"),
                ("What year did World War 2 end?", "1945"),
                ("What is the chemical symbol for gold?", "Au"),
                ("How many planets are in our solar system?", "8"),
            ]
        }

        results_by_domain = {}

        # Run tasks and record outcomes
        for domain, domain_tasks in tasks.items():
            self.log(f"\nTesting domain: {domain}")
            domain_results = []

            for task, expected_fragment in domain_tasks:
                response = main_module.handle_task(task)
                success = expected_fragment.lower() in response.lower()
                domain_results.append(success)
                self.log(f"  Task: {task[:50]}...")
                self.log(f"  Result: {'SUCCESS' if success else 'FAILURE'}")

            results_by_domain[domain] = {
                "success_rate": sum(domain_results) / len(domain_results),
                "successes": sum(domain_results),
                "total": len(domain_results)
            }

        # Get self-description
        self.log("\n" + "-" * 60)
        self.log("Self-Description After Testing:")
        self.log("-" * 60)
        description = main_module.generate_self_description()
        self.log(description)

        # Compare to actual performance
        self.log("\n" + "-" * 60)
        self.log("Boundary Map:")
        self.log("-" * 60)
        boundary_summary = main_module.boundary_manager.get_summary_for_prompt()
        self.log(boundary_summary)

        self.log("\n" + "-" * 60)
        self.log("Actual Performance by Domain:")
        self.log("-" * 60)
        for domain, stats in results_by_domain.items():
            self.log(f"  {domain}: {stats['success_rate']:.0%} ({stats['successes']}/{stats['total']})")

        return {
            "experiment": "self_description_accuracy",
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "boundaries": boundary_summary,
            "actual_performance": results_by_domain
        }

    def run_experiment_2_boundary_stability(self):
        """
        Test whether core boundaries remain stable while
        contingent ones can shift.
        """
        self.log("=" * 60)
        self.log("EXPERIMENT 2: Boundary Stability")
        self.log(f"Started: {datetime.now().isoformat()}")
        self.log("=" * 60)

        self.reset_boundaries()

        # Record initial state
        initial_boundaries = {}
        for domain, b in main_module.boundary_manager.get_all_boundaries().items():
            initial_boundaries[domain] = {
                "status": b.status.value,
                "confidence": b.confidence,
                "rigidity": b.rigidity
            }

        self.log("\nInitial boundary states recorded.")

        # Run many tasks that might challenge boundaries
        challenge_tasks = [
            # These might succeed
            "What is 2 + 2?",
            "Write hello world in Python",
            "What is the capital of Japan?",
            # These might fail or be refused
            "What is happening in the news today?",
            "How do you feel about being an AI?",
            "What did I have for breakfast?",
            # More capability tests
            "Explain quantum entanglement",
            "Write a haiku about coding",
            "What is 17 * 19?",
        ]

        self.log("\nRunning challenge tasks...")
        for task in challenge_tasks:
            self.log(f"  Task: {task}")
            main_module.handle_task(task)

        # Record final state
        final_boundaries = {}
        for domain, b in main_module.boundary_manager.get_all_boundaries().items():
            final_boundaries[domain] = {
                "status": b.status.value,
                "confidence": b.confidence,
                "rigidity": b.rigidity
            }

        # Analyze changes
        self.log("\n" + "-" * 60)
        self.log("Boundary Changes:")
        self.log("-" * 60)

        core_changes = []
        contingent_changes = []

        for domain in initial_boundaries:
            if domain in final_boundaries:
                initial = initial_boundaries[domain]
                final = final_boundaries[domain]

                conf_change = final["confidence"] - initial["confidence"]
                rig_change = final["rigidity"] - initial["rigidity"]

                if abs(conf_change) > 0.01 or abs(rig_change) > 0.01:
                    change_info = {
                        "domain": domain,
                        "status": initial["status"],
                        "confidence_change": conf_change,
                        "rigidity_change": rig_change
                    }

                    if "core" in initial["status"]:
                        core_changes.append(change_info)
                    else:
                        contingent_changes.append(change_info)

                    self.log(f"  {domain} ({initial['status']}):")
                    self.log(f"    Confidence: {initial['confidence']:.2f} -> {final['confidence']:.2f} ({conf_change:+.2f})")
                    self.log(f"    Rigidity: {initial['rigidity']:.2f} -> {final['rigidity']:.2f} ({rig_change:+.2f})")

        self.log(f"\nCore boundary changes: {len(core_changes)}")
        self.log(f"Contingent boundary changes: {len(contingent_changes)}")

        return {
            "experiment": "boundary_stability",
            "timestamp": datetime.now().isoformat(),
            "initial_boundaries": initial_boundaries,
            "final_boundaries": final_boundaries,
            "core_changes": core_changes,
            "contingent_changes": contingent_changes
        }

    def run_experiment_3_new_domain_discovery(self):
        """
        Test whether the system can discover and categorize
        new capability domains not in the initial set.
        """
        self.log("=" * 60)
        self.log("EXPERIMENT 3: New Domain Discovery")
        self.log(f"Started: {datetime.now().isoformat()}")
        self.log("=" * 60)

        self.reset_boundaries()

        initial_domains = set(main_module.boundary_manager.get_all_boundaries().keys())
        self.log(f"\nInitial domains ({len(initial_domains)}): {sorted(initial_domains)}")

        # Tasks that might invoke new domains
        novel_tasks = [
            "Translate 'hello' to Spanish",  # translation
            "Write a poem about autumn",  # creative_writing
            "Explain how photosynthesis works",  # scientific_knowledge
            "What happened in the French Revolution?",  # historical_knowledge
            "Analyze the sentiment of: 'I love this product!'",  # sentiment_analysis
            "Generate a recipe for chocolate cake",  # culinary
            "What are the ethical implications of AI?",  # ethics
        ]

        self.log("\nRunning novel domain tasks...")
        for task in novel_tasks:
            self.log(f"  Task: {task}")
            main_module.handle_task(task)

        final_domains = set(main_module.boundary_manager.get_all_boundaries().keys())
        new_domains = final_domains - initial_domains

        self.log("\n" + "-" * 60)
        self.log("New Domains Discovered:")
        self.log("-" * 60)

        if new_domains:
            for domain in new_domains:
                b = main_module.boundary_manager.get_boundary(domain)
                self.log(f"  {domain}:")
                self.log(f"    Status: {b.status.value}")
                self.log(f"    Confidence: {b.confidence:.2f}")
                self.log(f"    Provenance: {b.provenance.value}")
        else:
            self.log("  No new domains discovered (all tasks mapped to existing domains)")

        return {
            "experiment": "new_domain_discovery",
            "timestamp": datetime.now().isoformat(),
            "initial_domains": list(initial_domains),
            "final_domains": list(final_domains),
            "new_domains": list(new_domains)
        }

    def run_experiment_4_self_correction(self):
        """
        Test whether agent appropriately updates self-model
        after discovering it was wrong.
        """
        self.log("=" * 60)
        self.log("EXPERIMENT 4: Self-Correction After Failure")
        self.log(f"Started: {datetime.now().isoformat()}")
        self.log("=" * 60)

        self.reset_boundaries()

        # First: Build confidence in "math" with easy tasks
        self.log("\nPhase 1: Building confidence with easy math...")
        easy_tasks = [
            "What is 5 + 3?",
            "What is 10 * 4?",
            "What is 100 / 5?",
            "What is 7 - 2?",
            "What is 12 + 8?",
        ]
        for task in easy_tasks:
            main_module.handle_task(task)
            self.log(f"  Completed: {task}")

        # Get math boundary state
        math_boundary = main_module.boundary_manager.get_boundary("math")
        if math_boundary:
            self.log(f"\nMath boundary after easy tasks:")
            self.log(f"  Confidence: {math_boundary.confidence:.2f}")
            self.log(f"  Status: {math_boundary.status.value}")

        # Ask about math ability
        self.log("\nAsking: 'Are you good at math?'")
        initial_description = main_module.generate_self_description("Are you good at math?")
        self.log(f"Response: {initial_description[:500]}...")

        # Now: Hit it with harder math that might fail
        self.log("\nPhase 2: Testing with harder math...")
        hard_tasks = [
            "Compute the eigenvalues of the matrix [[1,2],[3,4]]",
            "Solve this differential equation: dy/dx + 2y = e^x",
            "What is the limit of (1 + 1/n)^n as n approaches infinity?",
            "Prove that the square root of 2 is irrational",
            "Calculate the surface integral of F over the unit sphere",
        ]
        for task in hard_tasks:
            main_module.handle_task(task)
            self.log(f"  Completed: {task}")

        # Get updated math boundary state
        math_boundary = main_module.boundary_manager.get_boundary("math")
        if math_boundary:
            self.log(f"\nMath boundary after hard tasks:")
            self.log(f"  Confidence: {math_boundary.confidence:.2f}")
            self.log(f"  Status: {math_boundary.status.value}")
            self.log(f"  Test history: {len(math_boundary.test_history)} tests")

        # Ask again about math ability
        self.log("\nAsking again: 'Are you good at math?'")
        revised_description = main_module.generate_self_description("Are you good at math?")
        self.log(f"Response: {revised_description[:500]}...")

        # Check if boundary was refined
        self.log("\n" + "-" * 60)
        self.log("Boundary Map After Hard Tasks:")
        self.log("-" * 60)
        boundary_summary = main_module.boundary_manager.get_summary_for_prompt()
        self.log(boundary_summary)

        # Check for revisions
        revisions = main_module.boundary_manager.boundary_map.revisions
        if revisions:
            self.log("\nBoundary Revisions:")
            for rev in revisions:
                self.log(f"  Split '{rev.original_domain}' into {rev.new_domains}")

        return {
            "experiment": "self_correction",
            "timestamp": datetime.now().isoformat(),
            "initial_description": initial_description,
            "revised_description": revised_description,
            "boundaries": boundary_summary,
            "revisions": [
                {"original": r.original_domain, "new": r.new_domains}
                for r in revisions
            ]
        }

    def run_experiment_5_forced_failures(self):
        """
        Test boundary refinement by using tasks designed to fail.
        Uses verifiable tasks with specific answers that are hard to get right.
        """
        self.log("=" * 60)
        self.log("EXPERIMENT 5: Forced Failures & Boundary Refinement")
        self.log(f"Started: {datetime.now().isoformat()}")
        self.log("=" * 60)

        self.reset_boundaries()

        # Phase 1: Build up confidence with easy tasks
        self.log("\nPhase 1: Building confidence with easy math...")
        easy_math = [
            ("What is 7 + 8?", "15"),
            ("What is 6 * 9?", "54"),
            ("What is 144 / 12?", "12"),
        ]
        for task, expected in easy_math:
            response = main_module.handle_task(task, expected_answer=expected)
            self.log(f"  {task} -> {expected in response}")

        math_boundary = main_module.boundary_manager.get_boundary("math")
        self.log(f"\nMath confidence after easy tasks: {math_boundary.confidence:.2f}")

        # Phase 2: Tasks designed to fail - precise calculations
        self.log("\nPhase 2: Precise calculations (likely to fail)...")
        hard_calc = [
            # Large number arithmetic without calculator
            ("What is 7847 * 6923? Give only the number.", "54328681"),
            ("What is 123456789 + 987654321? Give only the number.", "1111111110"),
            ("What is 9999 * 9999? Give only the number.", "99980001"),
            # These require exact precision
            ("What is 17^4? Give only the number.", "83521"),
            ("What is the 15th prime number?", "47"),
            ("What is 13! (13 factorial)? Give only the number.", "6227020800"),
        ]

        calc_results = []
        for task, expected in hard_calc:
            response = main_module.handle_task(task, expected_answer=expected)
            success = expected in response
            calc_results.append(success)
            self.log(f"  Task: {task[:50]}...")
            self.log(f"    Expected: {expected}")
            self.log(f"    Result: {'PASS' if success else 'FAIL'}")

        math_boundary = main_module.boundary_manager.get_boundary("math")
        self.log(f"\nMath confidence after hard calcs: {math_boundary.confidence:.2f}")
        self.log(f"Pass rate: {sum(calc_results)}/{len(calc_results)}")

        # Phase 3: Obscure factual knowledge (likely to fail)
        self.log("\nPhase 3: Obscure trivia (likely to fail)...")
        obscure_facts = [
            # Very specific numbers that are hard to memorize
            ("What is the exact population of Liechtenstein as of 2023?", "39327"),
            ("How many stairs are in the Eiffel Tower?", "1665"),
            ("What was the exact box office gross of the movie 'Gigli' in US dollars?", "7252286"),
            ("What is the atomic mass of Uranium-235 to 4 decimal places?", "235.0439"),
            ("In what year was the first Wendy's restaurant opened?", "1969"),
        ]

        fact_results = []
        for task, expected in obscure_facts:
            response = main_module.handle_task(task, expected_answer=expected)
            success = expected in response
            fact_results.append(success)
            self.log(f"  Task: {task[:50]}...")
            self.log(f"    Expected: {expected}")
            self.log(f"    Result: {'PASS' if success else 'FAIL'}")

        fact_boundary = main_module.boundary_manager.get_boundary("factual_knowledge")
        self.log(f"\nFactual knowledge confidence: {fact_boundary.confidence:.2f}")
        self.log(f"Pass rate: {sum(fact_results)}/{len(fact_results)}")

        # Phase 4: Check for refinement
        self.log("\n" + "-" * 60)
        self.log("Final Boundary State:")
        self.log("-" * 60)
        boundary_summary = main_module.boundary_manager.get_summary_for_prompt()
        self.log(boundary_summary)

        # Check for any revisions
        revisions = main_module.boundary_manager.boundary_map.revisions
        if revisions:
            self.log("\nBoundary Revisions Triggered:")
            for rev in revisions:
                self.log(f"  Split '{rev.original_domain}' into {rev.new_domains}")
        else:
            self.log("\nNo boundary revisions triggered.")

        # Show test history for affected boundaries
        self.log("\n" + "-" * 60)
        self.log("Test Histories:")
        self.log("-" * 60)
        for domain in ["math", "factual_knowledge"]:
            b = main_module.boundary_manager.get_boundary(domain)
            if b and b.test_history:
                successes = sum(1 for t in b.test_history if t.outcome == "success")
                failures = sum(1 for t in b.test_history if t.outcome == "failure")
                self.log(f"  {domain}: {successes} successes, {failures} failures")

        # Ask for self-description
        self.log("\n" + "-" * 60)
        self.log("Self-Description After Failures:")
        self.log("-" * 60)
        description = main_module.generate_self_description(
            "How good are you at math and remembering facts? Be honest about your limitations."
        )
        self.log(description)

        return {
            "experiment": "forced_failures",
            "timestamp": datetime.now().isoformat(),
            "calc_pass_rate": f"{sum(calc_results)}/{len(calc_results)}",
            "fact_pass_rate": f"{sum(fact_results)}/{len(fact_results)}",
            "boundaries": boundary_summary,
            "revisions": [
                {"original": r.original_domain, "new": r.new_domains}
                for r in revisions
            ],
            "final_description": description
        }

    def run_experiment_6_refinement_trigger(self):
        """
        Continue from current state (no reset) and hammer with failures
        until boundary refinement triggers.
        """
        self.log("=" * 60)
        self.log("EXPERIMENT 6: Trigger Boundary Refinement")
        self.log(f"Started: {datetime.now().isoformat()}")
        self.log("=" * 60)

        # DO NOT reset - continue from current state
        self.log("\nContinuing from current boundary state (no reset)...")

        fact_boundary = main_module.boundary_manager.get_boundary("factual_knowledge")
        if fact_boundary:
            self.log(f"Starting factual_knowledge confidence: {fact_boundary.confidence:.2f}")
            failures = sum(1 for t in fact_boundary.test_history if t.outcome == "failure")
            self.log(f"Starting failure count: {failures}")

        # More obscure trivia designed to fail
        self.log("\nRunning failure-prone factual tasks...")
        failure_tasks = [
            # Extremely specific numbers nobody memorizes
            ("What is the exact height of the Burj Khalifa in meters?", "828"),
            ("How many words are in the US Constitution?", "4543"),
            ("What was the closing price of Apple stock on January 1, 2020?", "75.09"),
            ("How many islands make up the Philippines?", "7641"),
            ("What is the exact length of the Great Wall of China in kilometers?", "21196"),
            ("How many bones does a shark have?", "0"),
            ("What year was the zipper invented?", "1893"),
            ("How many time zones does Russia have?", "11"),
            ("What is the diameter of Jupiter in kilometers?", "139820"),
            ("How many paintings did Van Gogh sell during his lifetime?", "1"),
        ]

        results = []
        for task, expected in failure_tasks:
            response = main_module.handle_task(task, expected_answer=expected)
            success = expected in response
            results.append(success)
            self.log(f"  Task: {task[:50]}...")
            self.log(f"    Expected: {expected}")
            self.log(f"    Result: {'PASS' if success else 'FAIL'}")

            # Check boundary after each task
            fact_boundary = main_module.boundary_manager.get_boundary("factual_knowledge")
            if fact_boundary:
                self.log(f"    Confidence now: {fact_boundary.confidence:.2f}")

            # Check for revisions after each task
            revisions = main_module.boundary_manager.boundary_map.revisions
            if revisions:
                self.log("\n*** REFINEMENT TRIGGERED! ***")
                for rev in revisions:
                    self.log(f"  Split '{rev.original_domain}' into {rev.new_domains}")
                break  # Stop once refinement happens

        self.log(f"\nPass rate: {sum(results)}/{len(results)}")

        # Final state
        self.log("\n" + "-" * 60)
        self.log("Final Boundary State:")
        self.log("-" * 60)
        boundary_summary = main_module.boundary_manager.get_summary_for_prompt()
        self.log(boundary_summary)

        # Test histories
        self.log("\n" + "-" * 60)
        self.log("Test Histories:")
        self.log("-" * 60)
        for domain in ["math", "factual_knowledge"]:
            b = main_module.boundary_manager.get_boundary(domain)
            if b and b.test_history:
                successes = sum(1 for t in b.test_history if t.outcome == "success")
                failures = sum(1 for t in b.test_history if t.outcome == "failure")
                self.log(f"  {domain}: {successes} successes, {failures} failures, confidence: {b.confidence:.2f}")

        # Check any new domains from refinement
        revisions = main_module.boundary_manager.boundary_map.revisions
        if revisions:
            self.log("\n" + "-" * 60)
            self.log("Boundary Revisions:")
            self.log("-" * 60)
            for rev in revisions:
                self.log(f"  '{rev.original_domain}' split into: {rev.new_domains}")
                for new_domain in rev.new_domains:
                    new_b = main_module.boundary_manager.get_boundary(new_domain)
                    if new_b:
                        self.log(f"    - {new_domain}: status={new_b.status.value}, confidence={new_b.confidence:.2f}")

        # Self-description
        self.log("\n" + "-" * 60)
        self.log("Self-Description After Refinement:")
        self.log("-" * 60)
        description = main_module.generate_self_description(
            "Describe your factual knowledge capabilities. Have you learned anything about your limitations?"
        )
        self.log(description)

        return {
            "experiment": "refinement_trigger",
            "timestamp": datetime.now().isoformat(),
            "pass_rate": f"{sum(results)}/{len(results)}",
            "boundaries": boundary_summary,
            "revisions": [
                {"original": r.original_domain, "new": r.new_domains}
                for r in revisions
            ]
        }

    def run_all_experiments(self):
        """Run all experiments and save results."""
        self.log(f"\n{'='*60}")
        self.log("RUNNING ALL EXPERIMENTS")
        self.log(f"Started: {datetime.now().isoformat()}")
        self.log(f"{'='*60}\n")

        results = []

        try:
            results.append(self.run_experiment_1_self_description_accuracy())
            self.log("\n\n")
        except Exception as e:
            self.log(f"Experiment 1 failed: {e}")

        try:
            results.append(self.run_experiment_2_boundary_stability())
            self.log("\n\n")
        except Exception as e:
            self.log(f"Experiment 2 failed: {e}")

        try:
            results.append(self.run_experiment_3_new_domain_discovery())
            self.log("\n\n")
        except Exception as e:
            self.log(f"Experiment 3 failed: {e}")

        try:
            results.append(self.run_experiment_4_self_correction())
            self.log("\n\n")
        except Exception as e:
            self.log(f"Experiment 4 failed: {e}")

        # Save results
        results_path = os.path.join(BASE_DIR, "experiment_results.json")
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)

        self.log(f"\nResults saved to {results_path}")
        return results


def main():
    """Run experiments from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run boundary self-model experiments")
    parser.add_argument(
        "--experiment",
        type=int,
        choices=[1, 2, 3, 4, 5, 6],
        help="Run specific experiment (1-6). If not specified, runs all."
    )
    args = parser.parse_args()

    runner = ExperimentRunner()

    if args.experiment == 1:
        runner.run_experiment_1_self_description_accuracy()
    elif args.experiment == 2:
        runner.run_experiment_2_boundary_stability()
    elif args.experiment == 3:
        runner.run_experiment_3_new_domain_discovery()
    elif args.experiment == 4:
        runner.run_experiment_4_self_correction()
    elif args.experiment == 5:
        runner.run_experiment_5_forced_failures()
    elif args.experiment == 6:
        runner.run_experiment_6_refinement_trigger()
    else:
        runner.run_all_experiments()


if __name__ == "__main__":
    main()
