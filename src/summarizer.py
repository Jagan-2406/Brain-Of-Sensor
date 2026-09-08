"""
LLM Summarizer Module

Translates PriorityTag instances into plain-English event summaries.
Uses LLM strictly as a translator (never as a decision-maker) with constrained prompts,
output validation, and safe non-LLM fallback mechanisms.
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv
from priority_tag import PriorityTag

# Load environment variables from .env file
load_dotenv()

PLACEHOLDER_KEY = "your_anthropic_api_key_here"


def build_prompt(priority_tag: PriorityTag) -> str:
    """
    Constructs a strict, constrained prompt from PriorityTag fields only.
    """
    reasons_formatted = ", ".join(priority_tag.reason_codes) if priority_tag.reason_codes else "None (normal baseline activity)"
    
    prompt = f"""Using only the data provided below, write one plain-English sentence (maximum 25 words) describing this event. Do not add any information, speculation, or context not present in the data. Do not change or reinterpret the urgency level.

Data:
- Zone: {priority_tag.zone}
- Object Detected: {priority_tag.object}
- Timestamp: {priority_tag.timestamp}
- Urgency Level: {priority_tag.urgency}
- Detection Confidence: {priority_tag.confidence}
- Reason Codes: {reasons_formatted}
- Live Count (Current Hour): {priority_tag.live_count}
- Historical 30-Day Average: {priority_tag.historical_avg}
"""
    return prompt


def fallback_summarize(priority_tag: PriorityTag) -> str:
    """
    Generates a safe, deterministic non-LLM summary string directly from tag fields.
    Used when API key is unconfigured, network fails, or validation flags an issue.
    """
    if priority_tag.reason_codes:
        reasons_str = f"reasons: {', '.join(priority_tag.reason_codes)}"
    else:
        reasons_str = "normal activity"

    return (
        f"In {priority_tag.zone}, a {priority_tag.object} was detected with {priority_tag.urgency} urgency "
        f"({reasons_str}; count: {priority_tag.live_count} vs avg: {priority_tag.historical_avg})."
    )


def summarize_event(priority_tag: PriorityTag) -> str:
    """
    Sends the PriorityTag prompt to Anthropic Claude API to generate a 1-sentence summary.
    Falls back gracefully to fallback_summarize() if key is missing/placeholder or on API errors.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    # If key is missing, empty, or placeholder, return fallback summary immediately
    if not api_key or api_key == PLACEHOLDER_KEY:
        return fallback_summarize(priority_tag)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = build_prompt(priority_tag)

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=80,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )

        if response.content and len(response.content) > 0:
            summary = response.content[0].text.strip()
            return summary
        else:
            return fallback_summarize(priority_tag)
            
    except Exception as e:
        print(f"[Summarizer Warning] LLM API call failed ({e}). Using deterministic fallback.")
        return fallback_summarize(priority_tag)


def validate_summary(summary_text: str, priority_tag: PriorityTag) -> str:
    """
    Validates LLM output against the PriorityTag:
    1. Ensures summary length does not exceed 40 words.
    2. Checks for urgency contradictions (e.g. summary saying 'low' when tag is 'high').

    Returns validated summary_text or fallback_summarize() if invalid.
    """
    words = summary_text.split()
    if len(words) > 40:
        print(f"[Validation Failed] Summary exceeded 40 words ({len(words)} words). Using fallback.")
        return fallback_summarize(priority_tag)

    summary_lower = summary_text.lower()
    tag_urgency = priority_tag.urgency.lower()

    # Check for direct contradictions (e.g. mentioning wrong urgency level)
    other_urgencies = {"low", "medium", "high"} - {tag_urgency}
    for wrong_urgency in other_urgencies:
        # Check if wrong urgency word is used as a descriptor in summary
        if f"{wrong_urgency} urgency" in summary_lower or f"{wrong_urgency} priority" in summary_lower:
            print(f"[Validation Failed] Summary mentioned '{wrong_urgency}' while tag urgency is '{tag_urgency}'. Using fallback.")
            return fallback_summarize(priority_tag)

    return summary_text
