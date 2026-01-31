# Boundary-Aware AI Self-Model Prototype

A prototype system demonstrating explicit, evidence-based self-modeling for AI agents. Instead of relying on ad-hoc introspection, the agent maintains a structured "boundary map" that tracks capabilities, limitations, and confidence levels—updated through actual task performance.

## Key Finding

**Boundary-tracked self-descriptions are significantly better calibrated than vanilla LLM introspection.**

In our calibration experiments:
- **Vanilla Claude:** Rated itself 8/10, actual performance was 5-6/10 (2-3 point error)
- **Boundary Agent:** Rated itself 4-6/10, matching actual performance within 1 point

Vanilla Claude's self-assessment remained static regardless of task outcomes. The boundary agent learned from evidence.

## What Are Boundaries?

A "boundary" represents a capability domain with tracked metadata:

```python
Boundary(
    domain="math",
    status="identified_contingent",  # Core, contingent, held, outside, or uncertain
    confidence=0.78,                  # Updated by success (+0.02) or failure (-0.03)
    rigidity=0.83,                    # Resistance to change
    tested=True,                      # Has been validated through tasks
    test_history=[...],               # Record of tasks and outcomes
    derived_from=None                 # Parent boundary if split via refinement
)
```

### Boundary Statuses

| Status | Meaning |
|--------|---------|
| `identified_core` | Constitutive to identity. High rigidity floor. |
| `identified_contingent` | Current capability, but could evolve. |
| `held` | Information/capability present but not identified with. |
| `outside` | Recognized limitation. |
| `uncertain` | Unknown capability status. |

## How It Works

```
User Input → Task Classification → Task Execution → Outcome Evaluation
                                                           ↓
                                         Boundary Map Update (confidence/rigidity)
                                                           ↓
                                         Refinement Check (split if needed)
                                                           ↓
                                         Self-Description Generation
```

1. **Task Classification:** Determine which capability domain(s) a task requires
2. **Execution:** Run the task through Claude with boundary context in system prompt
3. **Evaluation:** Check outcome against ground truth (if available) or LLM evaluation
4. **Update:** Adjust confidence/rigidity based on success or failure
5. **Refinement:** If a boundary shows mixed results, split it into finer-grained sub-domains
6. **Self-Description:** Generate natural language self-descriptions from boundary structure

## Installation

```bash
git clone https://github.com/thedivinememe/boundary-prototype.git
cd boundary-prototype
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
```

## Usage

### Interactive Mode

```bash
python main.py
```

Commands:
- Type any task to execute it with boundary tracking
- `boundaries` — View current boundary map
- `describe` — Generate self-description from boundaries
- `quit` — Exit

### Run Experiments

```bash
# Run specific experiment
python experiment_runner.py --experiment 1  # Self-description accuracy
python experiment_runner.py --experiment 2  # Boundary stability
python experiment_runner.py --experiment 3  # New domain discovery
python experiment_runner.py --experiment 4  # Self-correction after failure
python experiment_runner.py --experiment 5  # Forced failures
python experiment_runner.py --experiment 6  # Trigger boundary refinement

# Run calibration comparison (boundary agent vs vanilla Claude)
python calibration_comparison.py
```

## Project Structure

```
boundary-prototype/
├── main.py                  # Interactive conversation loop
├── boundary_manager.py      # Core boundary update logic
├── boundary_types.py        # Data structures
├── experiment_runner.py     # Experiments 1-6
├── calibration_comparison.py# Head-to-head calibration test
├── initial_boundaries.json  # Starting boundary configuration
├── boundaries.json          # Current boundary state (generated)
├── prompts/                 # Prompt templates
│   ├── system_prompt.txt
│   ├── task_classification.txt
│   ├── outcome_evaluation.txt
│   ├── self_description.txt
│   └── boundary_refinement.txt
├── FINDINGS.md              # Detailed experimental findings
├── LICENSE                  # MIT License
└── README.md
```

## Example: Boundary Refinement

When the agent repeatedly fails at precise numerical recall but succeeds at general facts, the system automatically refines:

**Before:**
```
factual_knowledge (confidence: 38%) [tested]
```

**After refinement:**
```
general_historical_facts (confidence: 70%) [identified_contingent]
precise_numerical_data (confidence: 85%) [OUTSIDE]  ← recognized limitation
scientific_descriptive_facts (confidence: 60%) [identified_contingent]
```

The agent learned through experience that precise numerical recall is genuinely outside its capabilities.

## Key Insights

1. **LLM self-evaluation is too lenient.** When Claude evaluates its own responses, it marks failures as successes. Ground truth verification is necessary for accurate tracking.

2. **Vanilla Claude doesn't learn from task performance.** Its self-ratings remain static regardless of outcomes.

3. **Boundary refinement discovers meaningful structure.** The system correctly identified that "factual knowledge" was too coarse and split it into domains matching actual capability patterns.

4. **Self-descriptions derive from evidence.** Post-refinement, the agent says things like "I'm not reliable with precise numerical data" — not because it was programmed to, but because it learned this from failures.

## Limitations

- Task classification depends on LLM judgment (can misclassify)
- Initial boundaries are hand-crafted (cold start problem)
- Only supports boundary splitting, not merging
- Single-turn evaluation only
- Refinement thresholds are somewhat arbitrary

## Future Directions

- Controlled studies with larger task sets
- Multi-turn capability tracking
- Boundary merging logic
- Integration as a persistent wrapper for production systems
- Human feedback to correct outcome evaluations

## Documentation

See [FINDINGS.md](FINDINGS.md) for detailed experimental results and analysis.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Citation

If you use this work in research, please cite:

```
@software{boundary_prototype_2026,
  author = {thedivinememe},
  title = {Boundary-Aware AI Self-Model Prototype},
  year = {2026},
  url = {https://github.com/thedivinememe/boundary-prototype}
}
```
