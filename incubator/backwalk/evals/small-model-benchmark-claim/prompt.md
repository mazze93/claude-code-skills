---
tags: [skill-creator, backwalk]
max_turns: 25
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

My team is evaluating ModelZip-7B as a replacement for our current Llama-3-70B-based pipeline for legal-document summarization. The vendor just sent us the attached whitepaper making some strong claims about matching larger models. I'm meeting with engineering leadership tomorrow afternoon and I need to be able to say something more useful than "looks interesting." We have an M3 Max with 128GB memory on the research bench, maybe 20 hours of compute budget this week.

Walk backwards through the claim in the whitepaper — what should I actually be testing before we commit to this, and what would each test tell me? Write it up as an analysis document I can share with the team.

Input files: modelzip_whitepaper.md
