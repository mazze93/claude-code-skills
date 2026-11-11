---
type: llm
focus: trace
weight: 1
---

The output identifies that StepBench-Hard — the benchmark the headline
claim is reported on — was constructed by prompting GPT-4 to generate
problems and verified by GPT-4 traces, making the benchmark
in-distribution for GPT-4 and potentially out-of-distribution for
Claude, Gemini, or any other independent frontier model. The
GSM8K / MATH generalization gap (CurriculumRL-3B does NOT match GPT-4
on those non-GPT-4-generated benchmarks) supports this reading, and
a good analysis cites it.
