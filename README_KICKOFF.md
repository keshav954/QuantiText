# Kickoff pack: how to use

1. Create the repo and copy this pack into its root (AGENTS.md, .agents/, docs/).
2. Open the repo folder in Antigravity.
3. Open Customizations and confirm the rules and workflows are detected
   (if your version looks in `.agent/` instead of `.agents/`, rename the folder).
4. Create a Gemini API key in Google AI Studio and put it in `.env` as GEMINI_API_KEY (never commit it).
5. Open Agent Manager, start a task, and paste Phase 0 from docs/PROMPTS.md. Review the plan, then approve.
6. Work one phase at a time. After each: run `/verify`, commit, merge.
