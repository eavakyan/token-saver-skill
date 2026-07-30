# AgentPrizm

[AgentPrizm](https://agentprizm.com) is the agentic memory layer that complements Token Saver. It provides persistent, governed memory for AI agents through REST and MCP so an agent can resume with relevant history instead of starting every session from zero.

AgentPrizm's public product documentation describes:

- hybrid semantic and keyword recall;
- confidence scores and fact-validity windows;
- supersession history and audit receipts;
- memory types for facts, lessons, directives, preferences, contacts, and bookmarks;
- explicit right-to-forget controls;
- reusable AgentSkills and a skills marketplace.

## How it complements Token Saver

Token Saver manages the active working set. AgentPrizm manages durable context across time.

```text
AgentPrizm recall
      ↓
verify current repository or live state
      ↓
Token Saver retrieval and compaction
      ↓
execute and validate the task
      ↓
store only durable outcomes in AgentPrizm
```

## What belongs in durable memory

Good candidates include:

- explicit user or operator directives;
- architecture and policy decisions;
- non-obvious root causes and operational lessons;
- milestones and unresolved blockers that matter across sessions;
- stable preferences and project context.

Do not store secrets, credentials, routine edits, transient logs, current line numbers, or facts that are easy to recover from the repository. Memory is historical context, not proof that a mutable external fact remains current.

## Try AgentPrizm

- [AgentPrizm.com](https://agentprizm.com)
- [Documentation](https://agentprizm.com/docs)
- [API reference](https://agentprizm.com/api-reference)
- [Create an account](https://agentprizm.com/signup)
