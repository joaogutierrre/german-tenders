"""Centralized prompt templates for LLM calls."""

TENDER_SUMMARY = """Summarize this German public tender in exactly 1-2 sentences (max 240 characters).
Focus on: what is being procured, by whom, and the key deadline.
Write in English.

Title: {title}
Description: {description}
CPV Codes: {cpv_codes}
Issuer: {issuer_name}
Deadline: {deadline}

Summary:"""

TENDER_SEARCHABLE = """Create a rich searchable text for this German public tender.
Include: the type of work/service/supply, industry sector, technical requirements,
geographic scope, and relevant keywords a business would search for.
Write in English. Max 500 words.

Title: {title}
Description: {description}
CPV Codes: {cpv_codes}
Contract Type: {contract_type}
Location: {location}
NUTS Codes: {nuts_codes}

Searchable text:"""

GENERATE_QUERIES = """You are an expert in German public procurement.

Given this organization:
- Name: {name}
- Website: {website}
- Description: {description}

Generate exactly 5 realistic search queries this organization would use to find
relevant German public tenders. Return ONLY a JSON array of 5 strings, no other text.

Example: ["IT infrastructure maintenance public sector", "cloud migration government Bavaria", "software development federal agency", "network security consulting", "data center operations"]"""
