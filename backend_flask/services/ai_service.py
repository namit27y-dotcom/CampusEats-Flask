import json
import re
import logging
from backend_flask.config import Config

logger = logging.getLogger(__name__)

def infer_is_veg(item):
    """Safely infer vegetarian status from item attributes."""
    text = f"{item.get('name', '')} {item.get('description', '')} {item.get('category', '')}".lower()
    non_veg_keywords = ['chicken', 'egg', 'fish', 'mutton', 'meat', 'prawn', 'pork', 'beef', 'non-veg', 'nonveg']
    return not any(kw in text for kw in non_veg_keywords)

def infer_prep_time(item):
    """Safely infer prep time in minutes based on category."""
    category = str(item.get('category', '')).lower()
    if any(k in category for k in ['beverage', 'drink', 'tea', 'coffee']):
        return 3
    if any(k in category for k in ['snack', 'breakfast']):
        return 5
    if any(k in category for k in ['meal', 'combo', 'lunch', 'thali']):
        return 10
    return 8

def generate_recommendations(prompt, catalog, budget=None, dietary=None, history_names=""):
    """
    Generate recommendations using Gemini 2.5 Flash if available,
    falling back to deterministic database heuristic matching.
    """
    trimmed_prompt = prompt.strip()
    api_key = Config.GEMINI_API_KEY
    ai_result = None

    if api_key and api_key not in ["MY_GEMINI_API_KEY", "YOUR_GEMINI_API_KEY"]:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            
            system_instruction = """You are CampusEats AI Cafeteria Assistant. 
Analyze the user's request and recommend meals strictly from the provided Menu Catalog.

RULES:
1. ONLY recommend items that exist in the Menu Catalog. Use their exact numeric "id".
2. NEVER hallucinate food items or invent new item IDs.
3. NEVER invent specific calorie, fat, or carb gram numbers since nutrition data is not in the database.
4. If the user asks general questions about the menu, vegetarian options, items under a budget, combos, or tastes, select relevant items from the catalog and explain clearly in the summary and item reasons.
5. Output MUST be valid JSON matching this schema:
{
  "recommendations": [
    {
      "menuItemId": <number>,
      "name": "<string>",
      "reason": "<short explanation why this fits budget/diet/speed/preference>",
      "estimatedWaitMinutes": <number>
    }
  ],
  "summary": "<one or two sentence helpful and friendly response answering the student's question>"
}"""

            user_content = f"""User Request: "{trimmed_prompt}"
User Filters: Budget = {f'₹{budget}' if budget else 'Any'}, Diet = {dietary or 'Any'}
Recent Student Favorites: {history_names or 'None'}

Available Menu Catalog:
{json.dumps(catalog, indent=2)}

Provide your response strictly in the JSON format requested."""

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_content,
                config={
                    'system_instruction': system_instruction,
                    'response_mime_type': 'application/json'
                }
            )

            response_text = response.text.strip() if response.text else ""
            if response_text:
                # Clean fences if needed
                response_text = re.sub(r'^```(?:json)?\s*', '', response_text, flags=re.IGNORECASE)
                response_text = re.sub(r'\s*```$', '', response_text)
                first_brace = response_text.find('{')
                last_brace = response_text.rfind('}')
                if first_brace != -1 and last_brace != -1:
                    response_text = response_text[first_brace:last_brace + 1]
                ai_result = json.loads(response_text)
        except Exception as e:
            logger.warning(f"Gemini API call notice, falling back to database heuristic matcher: {e}")

    # Fallback to database heuristic
    if not ai_result or not isinstance(ai_result.get("recommendations"), list):
        ai_result = generate_database_heuristics(trimmed_prompt, catalog, budget, dietary)

    return ai_result

def generate_database_heuristics(prompt, catalog, budget=None, dietary=None):
    """Deterministic recommendation engine based on menu attributes."""
    lower = (prompt or "").lower()
    filtered = list(catalog)

    # Budget filter
    max_budget = budget
    if not max_budget:
        match = re.search(r'under\s*₹?(\d+)', lower)
        if match:
            max_budget = float(match.group(1))
    
    if max_budget:
        filtered = [item for item in filtered if float(item.get('price', 0)) <= float(max_budget)]

    # Dietary filter
    is_veg_query = (dietary == "veg") or ("veg" in lower) or ("vegetarian" in lower)
    if is_veg_query:
        filtered = [item for item in filtered if item.get('isVeg', True)]

    # Fast/Rush filter
    is_fast_query = any(k in lower for k in ["fast", "quick", "rush", "hurry"])
    if is_fast_query:
        filtered.sort(key=lambda x: x.get('prepTimeMinutes', 8))
    else:
        stop_words = {'and', 'for', 'the', 'what', 'can', 'eat', 'under', 'which', 'items', 'are', 'you', 'have', 'show', 'suggest', 'food'}
        keywords = [w for w in re.split(r'[\s,?.!]+', lower) if len(w) > 2 and w not in stop_words]
        if keywords:
            def score(item):
                text = f"{item.get('name', '')} {item.get('description', '')} {item.get('category', '')}".lower()
                return sum(1 for kw in keywords if kw in text)
            filtered.sort(key=score, reverse=True)
        else:
            filtered.sort(key=lambda x: float(x.get('price', 0)))

    top_items = filtered[:4]
    recommendations = []
    for item in top_items:
        prep_time = item.get('prepTimeMinutes', 8)
        price = item.get('price', 0)
        if max_budget:
            reason = f"Priced at ₹{price}, well within your ₹{max_budget} budget"
        elif is_fast_query:
            reason = f"Ready in ~{prep_time} mins for a quick break"
        else:
            reason = "Freshly prepared and available at the cafeteria"

        recommendations.append({
            "menuItemId": item.get("id"),
            "name": item.get("name"),
            "reason": reason,
            "estimatedWaitMinutes": prep_time
        })

    if recommendations:
        if max_budget:
            summary = f"Found {len(recommendations)} great option{'s' if len(recommendations) > 1 else ''} under ₹{max_budget}."
        elif is_veg_query:
            summary = f"Found {len(recommendations)} delicious vegetarian option{'s' if len(recommendations) > 1 else ''}."
        else:
            summary = f"Here are {len(recommendations)} top recommendations matching \"{prompt}\"."
    else:
        summary = "No matching menu items found for your specific criteria."

    return {
        "recommendations": recommendations,
        "summary": summary
    }
