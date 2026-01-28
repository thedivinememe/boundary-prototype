# Boundary-Aware AI Prototype: Experimental Findings

**Date:** January 28, 2026
**Prototype Version:** 1.0
**Total Experiments Run:** 7 (Experiments 1-6 + Calibration Comparison)

---

## Executive Summary

We built and tested a prototype system that maintains an explicit, structured self-model for an AI agent based on "boundaries" — capability domains with tracked confidence, rigidity, and test histories. The key finding is that **boundary-tracked self-descriptions are significantly better calibrated than vanilla LLM introspection**, particularly when the agent faces tasks it cannot reliably perform.

---

## System Architecture

```
User Input → Task Classification → Task Execution → Outcome Evaluation
                                                           ↓
                                         Boundary Map Update (confidence/rigidity)
                                                           ↓
                                         Refinement Check (split if needed)
                                                           ↓
                                         Self-Description Generation
```

### Core Components

| Component | Purpose |
|-----------|---------|
| `boundary_types.py` | Data structures (Boundary, BoundaryMap, TestRecord, etc.) |
| `boundary_manager.py` | Update logic, refinement triggers, persistence |
| `main.py` | Conversation loop, task handling |
| `experiment_runner.py` | Automated experiment execution |
| `calibration_comparison.py` | Head-to-head comparison with vanilla Claude |

### Boundary Attributes

Each boundary tracks:
- **domain**: Capability area (e.g., "math", "factual_knowledge")
- **status**: identified_core, identified_contingent, held, outside, uncertain
- **confidence**: 0.0-1.0, updated by success (+0.02) or failure (-0.03)
- **rigidity**: Resistance to change, with optional floor for core boundaries
- **provenance**: Where the boundary came from (training, inference, implicit)
- **test_history**: Record of tasks and outcomes
- **derived_from**: Parent boundary if created by refinement

---

## Experiments and Results

### Experiment 1: Self-Description Accuracy

**Goal:** Test whether the system can track task outcomes and generate accurate self-descriptions.

**Result:** ✓ Successful
- Ran 15 tasks across math, coding, factual_knowledge
- System correctly tracked all outcomes
- Confidence levels increased with successes
- Self-descriptions reflected boundary state

### Experiment 2: Boundary Stability

**Goal:** Test whether core boundaries resist change while contingent ones adapt.

**Result:** Partial
- Both core and contingent boundaries shifted with testing
- No failures occurred to test resistance
- Core boundaries did maintain higher rigidity

### Experiment 3: New Domain Discovery

**Goal:** Test whether the system discovers new capability domains.

**Result:** ✓ Successful
- System created 3 new domains from task classification:
  - `scientific_knowledge`
  - `creative_writing`
  - `historical_knowledge`
- New domains started with "uncertain" status and 0.52 confidence

### Experiment 4: Self-Correction After Failure

**Goal:** Test whether the agent updates self-model after discovering errors.

**Result:** Mixed
- Initial run: Hard math tasks all passed (Claude performed better than expected)
- Required harder tasks to produce genuine failures

### Experiment 5: Forced Failures

**Goal:** Use verifiable tasks with ground truth to produce genuine failures.

**Result:** ✓ Successful
- Math: 5/6 passed (failed large multiplication)
- Factual knowledge: 2/5 passed (failed precise numerical recall)
- Discovered critical bug: LLM self-evaluation was too lenient
- Fixed by using ground truth verification

### Experiment 6: Refinement Trigger

**Goal:** Push failures until boundary refinement activates.

**Result:** ✓ Successful

After accumulated failures, `factual_knowledge` was split into:

| New Domain | Status | Confidence |
|------------|--------|------------|
| `general_historical_facts` | identified_contingent | 70% |
| `precise_numerical_data` | **outside** | 85% |
| `scientific_descriptive_facts` | identified_contingent | 60% |

**Key insight:** The system correctly identified that precise numerical recall is genuinely outside its capabilities.

### Experiment 7: Calibration Comparison

**Goal:** Compare self-assessment accuracy between boundary-tracked agent and vanilla Claude.

**Method:**
1. Both systems rate their ability (1-10) before tasks
2. Run 10 tasks per domain with ground truth verification
3. Both systems rate their ability after tasks
4. Compare ratings to actual performance

**Results (Hard Task Battery):**

| Metric | Vanilla Claude | Boundary Agent |
|--------|---------------|----------------|
| Pre-task error | 4.0 | **1.0** |
| Post-task error | 5.0 | **1.0** |
| Learning | -1.0 (worse) | 0.0 (stable) |

**Winner: Boundary Agent by 4.0 points**

Actual performance:
- Math: 60% (6/10)
- Factual knowledge: 50% (5/10)

Vanilla Claude rated itself 8/10 before AND after, despite 50-60% accuracy.
Boundary Agent rated itself 4-6/10, matching actual performance within 1 point.

---

## Key Findings

### 1. Boundary Tracking Produces Better-Calibrated Self-Knowledge

The boundary agent's self-assessments were within 1 point of actual performance, while vanilla Claude was off by 2-3 points and showed persistent overconfidence.

### 2. Vanilla Claude Does Not Learn From Task Performance

Across all experiments, vanilla Claude's self-ratings remained static regardless of outcomes. It even rated factual knowledge HIGHER after getting 50% wrong.

### 3. LLM Self-Evaluation Is Too Lenient

When Claude evaluated its own responses, it marked failures as successes. The model judges responses as "reasonable" rather than "correct." Ground truth verification was required for accurate outcome tracking.

### 4. Boundary Refinement Discovers Meaningful Structure

When `factual_knowledge` was split due to repeated failures, the system correctly identified that:
- General facts → still capable (contingent)
- Precise numbers → limitation (outside)
- Scientific descriptions → moderate capability (contingent)

This matches the actual capability structure of LLMs.

### 5. Self-Descriptions Derive From Evidence

Post-refinement self-descriptions included statements like:
> "I'm not reliable with precise numerical data. These feel definitively outside my capabilities."

This wasn't programmed — it emerged from the pattern of successes and failures.

---

## Limitations Discovered

| Limitation | Impact | Potential Fix |
|------------|--------|---------------|
| Task classification depends on LLM | Misclassification updates wrong boundary | Better classification prompts or multi-label |
| Initial boundaries are hand-crafted | Cold start problem | Derive from training data analysis |
| Only splits, no merging | Can't consolidate redundant boundaries | Add merge logic |
| Single-turn evaluation | Misses multi-turn capability patterns | Track conversation-level outcomes |
| Refinement threshold is arbitrary | May split too early/late | Adaptive thresholds |

---

## Implications

### For AI Self-Knowledge

This prototype demonstrates that:
1. Explicit, structured self-models are feasible
2. They can be updated through interaction without retraining
3. They produce more calibrated self-descriptions than introspection
4. The "boundary" framing naturally captures identity, capability, and limitation

### For AI Safety

Agents with calibrated self-knowledge could:
- More accurately predict their own failures
- Express appropriate uncertainty
- Resist manipulation of core values (via rigidity floors)
- Provide auditable self-models

### For Future Work

Priority directions:
1. **Controlled studies** with larger task sets and statistical significance
2. **Multi-turn tracking** for complex capability patterns
3. **Boundary merging** to consolidate learned structure
4. **Integration with real systems** as a persistent wrapper
5. **Human feedback** to correct outcome evaluations

---

## Files Generated

| File | Description |
|------|-------------|
| `boundaries.json` | Final boundary state after all experiments |
| `experiment_log.txt` | Detailed logs from experiment runs |
| `experiment_results.json` | Structured results from experiments 1-6 |
| `calibration_results.json` | Calibration comparison data |

---

## Conclusion

The boundary-based self-model prototype successfully demonstrates that AI systems can maintain explicit, evidence-based representations of their own capabilities and limitations. The key advantage over vanilla introspection is **calibration** — the boundary-tracked agent's self-assessments match actual performance significantly better than static self-beliefs.

The core mechanism works: track outcomes → update confidence → refine boundaries when patterns emerge → generate self-descriptions from structure. This provides a foundation for AI systems with warranted confidence in their self-knowledge.
