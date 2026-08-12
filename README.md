# Codebase Crew

A multi-agent crew (built on **LangGraph**) that reads GitHub issues, plans and writes
fixes, tests them, reviews its own work, and opens pull requests.


```
                          ┌─────────────┐
   GitHub issue  ──────▶  │   Triager   │  classify + gather context
                          └──────┬──────┘
                      actionable?│ ────── no ──▶ [comment & close]
                                 │ yes
                          ┌──────▼──────┐
                          │   Planner   │  fix plan + target files
                          └──────┬──────┘
                          ┌──────▼──────┐
                  ┌─────▶ │    Coder    │  edit files on a branch
                  │       └──────┬──────┘
                  │       ┌──────▼──────┐
                  │       │   Tester    │  write/run tests
                  │       └──────┬──────┘
              reject│       ┌────▼─────┐
              (loop │  ◀────│ Reviewer │  review diff
            w/ cap) │       └────┬─────┘
                  └────────────  │ approve
                          ┌──────▼──────┐
                          │  PR Agent   │  open PR  ◀── human gate
                          └─────────────┘
```
