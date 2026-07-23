# `application/graph/builder.py` — LangGraph wiring (the supervisor)

**Layer:** application/graph · **Stage:** 5 · **ADR:** AD-1, AD-2, AD-3 · **Pattern:** Orchestration + State

## 🎯 කාර්යය
Agents ඔක්කොම **supervised graph** එකකට assemble කරන එකම තැන (**LangGraph import වෙන එකම file එක**).
Answering team `A1→A6` + bounded Acquisition loop `B1→B4`, **state-driven supervisor** එකක් (conditional
edges), A3 human-in-the-loop `interrupt()` එකත් සමඟ.

## 🔍 Code Walkthrough
`build_graph(deps, *, checkpointer=None)`:
1. **Nodes** — a1…a6, b1…b4 agents `deps` වලින් construct (ports + tunables inject).
2. **Wiring nodes** (agents නෙවෙයි, supervisor bookkeeping):
   - `_clarify_node` — A3 question එක UI එකට `interrupt()` කරලා pause; resume එකේදී answered slot fill.
   - `_enter_gap_node` — එක acquisition loop එකකට commit: `acquisition_loops + 1`, per-loop scratch reset.
3. **Edges + routers** (pure state functions, **LLM quota කිසිවක් නෑ**):

```
START → A1 → A2 ┬─ unknown ──────────────→ A4 → A5 ┬─ SUFFICIENT ─→ A6 → END
                └─ known → A3 ⇄ clarify ─→ A4       ├─ GAP, loops<N → enter_gap → B1→B2→B3→B4 → A4
                                                     └─ GAP, loops≥N → A6 (fallback) → END
```
   - `_route_after_identify` — unknown → A4 (clarify skip); known → A3.
   - `_route_after_clarify` — `pending_question` තියෙනවා නම් clarify (pause), නැත්නම් A4.
   - `_route_after_grade` — SUFFICIENT → A6; GAP & loops<N → enter_gap; **GAP & loops≥N → A6 (fallback)**.

`checkpointer` (SqliteSaver) — A3 interview pause/resume එකට **අවශ්‍යයි**; tests වල MemorySaver.

## 💡 Design decisions
- **Deterministic routing** — හැම transition එකක්ම `GraphState` ගේ function එකක් → traceable + free
  (plumbing එකට LLM නෑ).
- **Loop cap (AD-2)** `enter_gap` wiring එකේ, agents තුළ නෙවෙයි → agents framework-free.
- Bounded loop → free-tier quota protect (`loops ≥ N` → graceful fallback, grade GAP-ම).
