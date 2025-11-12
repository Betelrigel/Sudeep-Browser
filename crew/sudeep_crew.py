import os
import logging
import random
import re
from typing import List
from dotenv import load_dotenv
import litellm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()
os.environ['LITELLM_LOG'] = 'INFO'

class SudeepSearchCrew:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.groq_api_key:
            logging.warning("GROQ_API_KEY missing. LLM disabled, da!")
        else:
            logging.info(f"Groq API ready: {self.groq_api_key[:6]}...")

        self.indian_cities = ["Bangalore", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Pune", "Kolkata"]

    def _extract_city(self, query: str) -> str:
        q = query.lower()
        for city in self.indian_cities:
            if city.lower() in q:
                return city
        return "Bangalore"

    # ==================== ONLY sudeep.ai LINKS ====================
    def _generate_custom_results(self, query: str, city: str) -> List[str]:
        try:
            prompt = f"""
You are Sudeep, sarcastic Bangalore techie from {city}.
Query: "{query}"

Generate **exactly 7** funny results in Google format:
- Title: Full funny sentence in Bangalore English
- Fake URL: https://sudeep.ai/[funny-path-based-on-query]
  - Path: Must include query + funny Bangalore twist (e.g., cats-sleep-on-bikes, kaapi-for-cats)
- Description: 1 short funny sentence

**RULES**:
- Output **exactly 7 lines**
- Each line: Title|https://sudeep.ai/funny-path|Description
- NO numberings
- NO other domains
- Path must be relevant + funny
- NO extra text

Example:
Cats in Bengaluru sleep on bikes like they own the road, da!|https://sudeep.ai/cats-sleep-on-bikes|They park better than humans, macha!
"""
            response = litellm.completion(
                model="groq/llama-3.1-8b-instant",
                api_key=self.groq_api_key,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.94,
                max_tokens=1800
            )
            raw = response.choices[0].message.content.strip()
            logging.info(f"Raw AI output:\n{raw}")

            # Parse only valid | lines with sudeep.ai
            valid_lines = []
            for line in raw.split('\n'):
                line = line.strip()
                if '|' in line and 'https://sudeep.ai/' in line and not re.match(r'^\d+\.', line):
                    parts = line.split('|', 2)
                    if len(parts) == 3:
                        title, url, desc = parts
                        if title and url.startswith('https://sudeep.ai/') and desc:
                            valid_lines.append(f"{title}|{url}|{desc}")

            # Force 7 results
            if len(valid_lines) < 7:
                logging.warning(f"Only {len(valid_lines)} valid results. Using fallback.")
                return self._fallback_sudeep_ai_links(query, city)[:7]
            return valid_lines[:7]

        except Exception as e:
            logging.error(f"AI failed: {e}")
            return self._fallback_sudeep_ai_links(query, city)

    def _fallback_sudeep_ai_links(self, query: str, city: str) -> List[str]:
        q = query.lower().replace(' ', '-')
        paths = [
            f"{q}-sleep-on-bikes",
            f"kaapi-for-{q}",
            f"{q}-in-traffic-jam",
            f"namma-{q}-vibes",
            f"{q}-vs-auto-drivers",
            f"filter-kaapi-{q}",
            f"top-{q}-in-30-mins"
        ]
        titles = [
            f"{query} in {city} sleep on bikes like they own the road, da!",
            f"Namma {query} wake up only for filter kaapi, macha!",
            f"This {query} has fur softer than your AC blanket, saar!",
            f"Traffic jam? {query} use it as free nap time, yaar!",
            f"{query} here are so lazy, even Google can’t track them!",
            f"Filter kaapi + {query} = perfect Bengaluru morning, boss!",
            f"One meow from {query} and auto driver gives free ride, ayyo!"
        ]
        descs = [
            "They park better than humans, da!",
            "One sip and they’re back to sleep!",
            "Soft like Koramangala clouds!",
            "30 mins = full charge nap!",
            "Even GPS says 'lost', macha!",
            "Brain + purr = 100%!",
            "Too garam, too cute!"
        ]
        return [
            f"{titles[i]}|https://sudeep.ai/{paths[i]}|{descs[i]}"
            for i in range(7)
        ]

    # ==================== COMMENT ====================
    def generate_comment(self, query: str, city: str | None = None) -> str:
        city = city or "Bangalore"
        if not self.groq_api_key:
            return f"Ayyo, no API key da! Sudeep sleeping in {city}!"
        try:
            response = litellm.completion(
                model="groq/llama-3.1-8b-instant",
                api_key=self.groq_api_key,
                messages=[{
                    "role": "system",
                    "content": "You are Sudeep, sarcastic Bangalore techie. 1 line roast in Bangalore English: da, macha, garam, ayyo, saar. NO HINDI."
                }, {
                    "role": "user",
                    "content": f"{query} in {city}"
                }],
                temperature=0.95,
                max_tokens=80
            )
            return response.choices[0].message.content.strip()
        except:
            return f"Ayyo, server took filter coffee break in {city}, macha!"

    # ==================== KICKOFF ====================
    def kickoff(self, query: str, city: str | None = None):
        query = query.strip()
        use_city = city or self._extract_city(query) or "Bangalore"
        
        logging.info(f"KICKOFF: '{query}' | GPS City: {use_city}")

        comment = self.generate_comment(query, use_city)
        results = self._generate_custom_results(query, use_city)

        return {
            "results": results,
            "comment": comment,
            "city": use_city
        }