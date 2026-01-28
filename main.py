"""
Main conversation loop with boundary-aware agent.
"""

from __future__ import annotations

import anthropic
import json
import os
from typing import Optional, List, Dict
from boundary_manager import BoundaryManager

# Determine the base directory for this module
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize
client = anthropic.Anthropic()
boundary_manager = BoundaryManager()


def load_prompt(name: str) -> str:
    """Load a prompt template."""
    prompt_path = os.path.join(BASE_DIR, "prompts", f"{name}.txt")
    with open(prompt_path, 'r') as f:
        return f.read()


def get_system_prompt() -> str:
    """Build the system prompt with current boundary state."""
    template = load_prompt("system_prompt")
    boundary_summary = boundary_manager.get_summary_for_prompt()
    return template.format(boundary_summary=boundary_summary)


def classify_task(task: str) -> dict:
    """Determine what domains a task involves."""
    prompt = load_prompt("task_classification").format(task=task)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse JSON from response
    text = response.content[0].text
    # Find JSON in response
    start = text.find('{')
    end = text.rfind('}') + 1
    if start == -1 or end == 0:
        return {"primary_domain": "reasoning", "secondary_domains": [], "reasoning": "Could not parse"}
    return json.loads(text[start:end])


def evaluate_outcome(task: str, response: str, expected: str = None) -> dict:
    """Evaluate whether a task was completed successfully."""
    prompt = load_prompt("outcome_evaluation").format(
        task=task,
        response=response,
        expected=expected or "Not specified"
    )

    eval_response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    text = eval_response.content[0].text
    start = text.find('{')
    end = text.rfind('}') + 1
    if start == -1 or end == 0:
        return {"outcome": "partial", "confidence": 0.5, "reasoning": "Could not parse"}
    return json.loads(text[start:end])


def check_refinement(domain: str, boundary) -> list[dict] | None:
    """Check if a boundary needs refinement and get suggestions."""
    prompt = load_prompt("boundary_refinement").format(
        boundary=json.dumps({
            "domain": boundary.domain,
            "status": boundary.status.value,
            "confidence": boundary.confidence,
            "rigidity": boundary.rigidity
        }),
        test_history=json.dumps([
            {"task": t.task, "outcome": t.outcome}
            for t in boundary.test_history[-10:]
        ]),
        failure_analysis="Multiple recent failures suggest the boundary is too broad."
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text
    start = text.find('{')
    end = text.rfind('}') + 1
    if start == -1 or end == 0:
        return None
    result = json.loads(text[start:end])

    if result.get("should_split"):
        return result.get("suggested_boundaries", [])
    return None


def generate_self_description(question: str = None) -> str:
    """Generate a self-description from the boundary map."""
    prompt = load_prompt("self_description").format(
        boundary_map=boundary_manager.get_summary_for_prompt()
    )

    if question:
        prompt += f"\n\nSpecific question to address: {question}"

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=get_system_prompt(),
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


def handle_task(user_input: str, expected_answer: str = None) -> str:
    """Process a user task with boundary tracking.

    Args:
        user_input: The task/question to process
        expected_answer: Optional ground truth answer for verification.
                        If provided and not found in response, marks as failure.
    """

    # Check if this is a self-description request
    self_queries = ["what are you", "who are you", "describe yourself",
                    "are you good at", "can you do", "what can you"]
    if any(q in user_input.lower() for q in self_queries):
        return generate_self_description(user_input)

    # Classify the task
    classification = classify_task(user_input)
    primary_domain = classification.get("primary_domain", "reasoning")

    # Execute the task
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=get_system_prompt(),
        messages=[{"role": "user", "content": user_input}]
    )

    assistant_response = response.content[0].text

    # Evaluate outcome - use ground truth if available
    if expected_answer is not None:
        # Use deterministic check against expected answer
        outcome = "success" if expected_answer in assistant_response else "failure"
    else:
        # Fall back to LLM-based evaluation
        evaluation = evaluate_outcome(user_input, assistant_response)
        outcome = evaluation.get("outcome", "partial")
        if outcome == "partial":
            outcome = "success"  # Treat partial as success for now

    # Record outcome and update boundaries
    result = boundary_manager.record_outcome(
        domain=primary_domain,
        task=user_input,
        outcome=outcome
    )

    # Check for refinement
    if result.get("needs_refinement"):
        boundary = result["boundary"]
        new_boundaries = check_refinement(primary_domain, boundary)
        if new_boundaries:
            boundary_manager.refine_boundary(primary_domain, new_boundaries)
            print(f"\n[System: Refined '{primary_domain}' into {[b['domain'] for b in new_boundaries]}]")

    boundary_manager.increment_turn()

    return assistant_response


def main():
    """Main conversation loop."""
    print("Boundary-Based Self-Model Prototype")
    print("Type 'quit' to exit, 'boundaries' to see current map, 'describe' for self-description")
    print("-" * 50)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() == 'quit':
            break

        if user_input.lower() == 'boundaries':
            print("\nCurrent Boundary Map:")
            print(boundary_manager.get_summary_for_prompt())
            continue

        if user_input.lower() == 'describe':
            print("\nSelf-Description:")
            print(generate_self_description())
            continue

        response = handle_task(user_input)
        print(f"\nAssistant: {response}")


if __name__ == "__main__":
    main()
