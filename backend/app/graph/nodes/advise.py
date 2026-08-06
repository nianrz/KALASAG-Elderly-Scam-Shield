"""Advise node: explanation + next steps in the selected language.

Contacts come from keyed lookups and are injected as data with an
instruction to reproduce them verbatim. Brand detection is a deterministic
name scan against brand_rebuttals — never semantic.
"""

import json

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from app.graph.nodes.common import load_prompt, parse_json_reply
from app.graph.state import Advice, GraphState
from app.llm import invoke_with_retry
from app.retrieval import contacts as contacts_db
from app.schemas import Contact


class AdviseOutput(BaseModel):
    explanation: str
    next_steps: list[str]


def _detect_brand(text: str) -> contacts_db.BrandRebuttal | None:
    lowered = text.lower()
    for brand in contacts_db.known_brands():
        if brand.brand_name.lower() in lowered or brand.brand_id in lowered:
            return brand
    return None


def _gather_contacts(state: GraphState) -> tuple[list[Contact], str]:
    picked: list[Contact] = []
    data_lines: list[str] = []

    brand = _detect_brand(state["redacted_text"])
    if brand:
        picked.append(Contact(
            organisation=brand.brand_name,
            hotline=brand.official_hotline,
            url=brand.official_url,
        ))
        data_lines.append(
            f"- {brand.brand_name}: hotline {brand.official_hotline}, {brand.official_url}\n"
            f"  Official statement: \"{brand.rebuttal_quote}\""
        )

    for contact in contacts_db.top_contacts(n=2):
        if not contact.hotline and not contact.url:
            continue
        picked.append(Contact(
            organisation=contact.organisation,
            hotline=contact.hotline,
            url=contact.url,
        ))
        hotline = f"hotline {contact.hotline}, " if contact.hotline else ""
        data_lines.append(f"- {contact.organisation}: {hotline}{contact.url}")

    return picked, "\n".join(data_lines)


def make_advise(model: BaseChatModel):
    prompt = load_prompt("advise")

    def advise(state: GraphState) -> dict:
        picked, contacts_data = _gather_contacts(state)
        reply = invoke_with_retry(
            model,
            prompt.format(
                output_language=state["output_language"],
                contacts_data=contacts_data,
                verdict=state["verdict"],
                red_flags=json.dumps(
                    [f.model_dump() for f in state.get("red_flags", [])],
                    ensure_ascii=False,
                ),
                message_type=state["message_type"],
                redacted_text=state["redacted_text"],
            ),
        )
        output = AdviseOutput.model_validate(parse_json_reply(reply.content))
        return {
            "advice": Advice(
                explanation=output.explanation,
                next_steps=output.next_steps,
                contacts=picked,
            )
        }

    return advise
