Prefers simple terminal-style text, no heavy markdown, SHORT answers. Person/contact lookups: lead with the vault note link as > [[note_name]] and give contact details (email, LinkedIn).
§
User prefers a one-liner for git backup: git add . && git commit -m "this is obsidian backup commit and push" && git push origin main
§
User issues instructions as terse, often ALL-CAPS shorthand and expects them executed literally and completely — exact paths, folder spellings, and dates — preferring action over clarifying questions. Repeating an instruction verbatim signals it was not executed as literally intended, not that it was misheard. Telling the agent to 'reply back'/'send it' is itself the send authorization — send in the same pass, don't return a draft for re-approval.
§
Prefers reusing existing infra/credentials over building new — check for an existing resource (Key Vault secret, repo, plugin) first.
§
Standing instruction (2026-09-20): always record agent outputs to the vault unprompted — report under 4_Archieve/YYYY/MM/DD/ + a row in ai-agent-changelog.md; recording finishes a task. Repo-work outputs must show commit id + GitHub permalinks (commit and changed file).
§
Sends screenshots with no accompanying text and expects the agent to infer the task, probe the machine for evidence, and report findings with proof — not to ask what he meant.