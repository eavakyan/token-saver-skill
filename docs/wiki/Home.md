# Token Saver

Token Saver is an explicit-invocation Agent Skill and deterministic Python toolkit for reducing context and output tokens without dropping task-critical information.

It is part of a broader toolchain being developed by Gene Avakyan to help AI agents develop and operate businesses with stronger continuity, efficiency, evidence preservation, and human control.

## Start here

- [About Gene Avakyan](About-Gene-Avakyan)
- [Token Saver operations](Token-Saver-Operations)
- [AgentPrizm](AgentPrizm)
- [Repository README](https://github.com/eavakyan/token-saver-skill#readme)

## Token Saver and AgentPrizm

The tools solve different parts of the same problem:

| Tool | Primary role |
| --- | --- |
| Token Saver | Retrieve, compact, hand off, and validate the smallest sufficient context for the task in progress. |
| [AgentPrizm](https://agentprizm.com) | Preserve and recall durable, governed memory across agents, sessions, projects, and business workflows. |

A strong workflow begins by recalling durable project context from AgentPrizm, verifies mutable facts in the repository or live system, uses Token Saver to control the active working set, and writes back only durable outcomes worth remembering.

## What Token Saver protects

Token Saver is designed to preserve:

- the task goal, constraints, approval boundaries, and acceptance tests;
- explicit decisions and accepted artifacts;
- essential evidence, unresolved risks, and material uncertainty;
- exact language, code, commands, and numerical data when paraphrasing could change meaning.

It fails explicitly when protected material cannot fit within the requested budget instead of silently discarding required context.

## Try the memory layer

Visit [AgentPrizm.com](https://agentprizm.com) to explore the agentic memory layer and its REST and MCP integrations.
