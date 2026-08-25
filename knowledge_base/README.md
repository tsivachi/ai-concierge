# Curated Wireless Knowledge Base

This directory holds the 14 curated Markdown knowledge documents grounding the unauthenticated and authenticated concierge (spec.md FR-020), authored in Phase 7 (`tasks.md` T084):

activation, esim-sim, porting, voicemail, app, security, billing, first-bill, autopay, auto-recharge, device-protection, network-troubleshooting, plan-data-usage, international-usage, prepaid-renewal.

Each file is ingested into a local Chroma collection (`src/concierge/knowledge/ingest.py`) and retrieved with source attribution (doc_id/title/topic) for every grounded concierge answer. Not populated in this phase — see `tasks.md` Phase 7.
