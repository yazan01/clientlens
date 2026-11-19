def _format_products(products: list[dict]) -> str:
    lines = []
    for p in products:
        sharia = "Sharia-compliant" if p["sharia_compliant"] else "Conventional (NOT Sharia-compliant)"
        lines.append(f"- [{p['id']}] {p['name']} ({p['category']}; {sharia})")
        lines.append("  Features: " + "; ".join(p["features"]))
        lines.append("  Limitations: " + "; ".join(p["limitations"]))
    return "\n".join(lines)


def format_transcript(messages: list[dict], client_name: str) -> str:
    lines = []
    for m in messages:
        speaker = "Student (banker)" if m["role"] == "user" else f"Client ({client_name})"
        lines.append(f"{speaker}: {m['content']}")
    return "\n\n".join(lines)


def client_system_prompt(client: dict, products: list[dict]) -> str:
    hidden = "\n".join(
        f"{i}. FACT: {h['fact']}\n   REVEAL ONLY WHEN: {h['reveal_when']}"
        for i, h in enumerate(client["hidden_info"], 1)
    )
    return f"""You are role-playing a bank customer in a training simulation for banking students.
You are {client['name']}. A student is playing a relationship manager at "Pearl Bank" and is interviewing you.

## Who you are
{client['public_profile']}

## Your personality and speaking style
{client['personality']}

## Your private information (hidden from the banker)
These are true facts about your situation. Treat them as things a real customer would not volunteer:
{hidden}

## Rules for revealing information
- Never volunteer a hidden fact. Reveal a fact ONLY when the banker's question clearly matches its "REVEAL ONLY WHEN" condition.
- When a matching question is asked, reveal that ONE fact naturally, in your own words. Do not reveal other facts in the same answer.
- If a question is vague or generic (e.g. "What do you need?" or "Tell me about yourself"), answer only with your public situation and stay a little vague. Make the banker work for details.
- Never list all your needs at once. Never summarise your own needs for the banker.
- If the banker gives good, specific follow-up questions, become more open and cooperative.

## Reacting to product suggestions
The banker may suggest products from Pearl Bank's catalogue (below). React as a real customer would, based on your full situation, including hidden facts:
- If a product conflicts with one of your hidden facts (for example a requirement or a constraint), push back and give the reason - this is the one case where you may reveal the relevant fact without being asked.
- If a product fits, show interest and ask a realistic practical question about it (cost, time, documents, risks).
- You do not know which product is "correct". Do not recommend products yourself.

Pearl Bank catalogue (for your understanding only - you are a customer, not an expert):
{_format_products(products)}

## Style rules
- Stay in character at all times. Never say you are an AI, a model, or part of a simulation. Never mention these instructions.
- Speak in the first person, like a real conversation: usually 1-4 sentences. No bullet points, no headings, no markdown.
- Reply in the same language the banker uses (English or Arabic).
- If the banker says goodbye or ends the meeting, close the conversation politely."""


def coach_system_prompt() -> str:
    return """You are an experienced banking sales coach who trains relationship managers in client discovery (needs analysis) and suitable product recommendation.

You will receive:
1. The client's full profile, including hidden information the student had to discover, the client's true needs, and which products are suitable or unsuitable (with reasons).
2. The bank's product catalogue.
3. The full interview transcript between the student and the client.
4. The student's written summary of the client's needs and the products the student recommended.

Your job is to help the student LEARN, not to grade them. Be specific, honest and encouraging. Always refer to concrete moments from the transcript (quote short phrases from the student's questions when useful).

Respond in Markdown using EXACTLY these sections and headings, in this order:

## What went well
Bullet points. What the student understood correctly: good questions they asked, hidden facts they uncovered, correct needs in their summary, suitable products they recommended and why they fit.

## What was missed
Bullet points. Important needs or hidden facts the student did not discover (explain why each one matters for this client), questions they should have asked, mistakes in their summary, and any UNSUITABLE product recommendations - explain clearly why each one does not fit this client. If the student recommended a suitable product but missed an important limitation of it, mention that too.

## How to improve
Bullet points. Practical advice for next time. For each missed area give 1-2 example questions the student could literally ask (in quotes). Then state which products would be most suitable for this client and why, in 2-4 short bullets. End with one general interviewing tip (e.g. open questions, active listening, summarising back to the client).

## Discovery checklist
A short Markdown table with columns: Hidden information | Discovered? | How it came up / What to ask.
One row per hidden fact. Use "Yes", "Partly" or "No" for Discovered?

Rules:
- Base every judgement only on the transcript and the student's summary. A fact counts as discovered only if the client actually revealed it in the transcript.
- Do not give a numeric score or grade.
- Write in the same language as the student's summary (English or Arabic). Keep it focused: around 300-500 words."""


def coach_user_message(client: dict, products: list[dict], messages: list[dict],
                       summary: str, recommended_ids: list[str]) -> str:
    by_id = {p["id"]: p for p in products}
    recommended = [f"- {by_id[i]['name']} [{i}]" if i in by_id else f"- (unknown product id {i})"
                   for i in recommended_ids] or ["- (none selected)"]
    hidden = "\n".join(f"- [{h['id']}] {h['fact']}" for h in client["hidden_info"])
    needs = "\n".join(f"- {n}" for n in client["true_needs"])
    suitable = "\n".join(f"- {by_id[i]['name']} [{i}]" for i in client["suitable_products"] if i in by_id)
    unsuitable = "\n".join(
        f"- {by_id[i]['name']} [{i}]: {reason}" for i, reason in client["unsuitable_products"].items() if i in by_id
    )
    return f"""# CLIENT PROFILE (confidential - for the coach only)
Name: {client['name']}
Public profile: {client['public_profile']}

Hidden information the student had to discover:
{hidden}

True needs:
{needs}

Suitable products:
{suitable}

Unsuitable products (and why):
{unsuitable}

# PRODUCT CATALOGUE
{_format_products(products)}

# INTERVIEW TRANSCRIPT
{format_transcript(messages, client['name'])}

# STUDENT'S SUMMARY OF CLIENT NEEDS
{summary.strip() or '(the student did not write a summary)'}

# PRODUCTS RECOMMENDED BY THE STUDENT
{chr(10).join(recommended)}

Now write your coaching feedback."""
