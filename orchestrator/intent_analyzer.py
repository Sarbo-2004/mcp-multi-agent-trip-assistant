import json
from typing import Any, Dict, List, Optional

import spacy
import google.generativeai as genai

from config.settings import api_settings
from config.constants import (
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
)
from schemas.trip_schema import TripRequest


class IntentAnalyzer:
    def __init__(self, confidence_threshold: float = 0.70):
        self.confidence_threshold = confidence_threshold

        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.nlp = spacy.blank("en")
            self.nlp.add_pipe("sentencizer")

        self.model = None

        if api_settings.gemini_api_key:
            genai.configure(api_key=api_settings.gemini_api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")

    def analyze(self, user_query: str) -> TripRequest:
        spacy_request = self._analyze_with_spacy(user_query)

        if self._is_spacy_result_good_enough(spacy_request):
            return spacy_request

        gemini_request = self._analyze_with_gemini(user_query, spacy_request)

        if gemini_request:
            return gemini_request

        return spacy_request

    def _analyze_with_spacy(self, user_query: str) -> TripRequest:
        doc = self.nlp(user_query)

        source = self._extract_source_from_dependency(doc)
        destination = self._extract_destination_from_dependency(doc, source)

        entities = self._extract_entities(doc)

        if not source:
            source = entities.get("source")

        if not destination:
            destination = entities.get("destination")

        month = entities.get("month")
        days = entities.get("days")
        travelers = entities.get("travelers")

        interests = self._extract_interest_candidates(doc)
        budget = self._extract_budget_candidate(doc)

        request = TripRequest(
            user_query=user_query,
            source=source,
            destination=destination,
            month=month,
            days=days,
            budget=budget,
            travelers=travelers,
            interests=interests,
            parser_used="spacy",
        )

        request.suggested_agents = self._infer_agents(request)
        request.missing_fields = self._find_missing_fields(request)
        request.confidence = self._score_spacy_result(request)

        return request

    def _extract_source_from_dependency(self, doc) -> Optional:
        for token in doc:
            if token.text.lower() == "from":
                location = self._collect_prepositional_object(token)

                if location:
                    return location

        return None

    def _extract_destination_from_dependency(self, doc, source: Optional[str]) -> Optional:
        for token in doc:
            if token.text.lower() == "to":
                location = self._collect_prepositional_object(token)

                if location and location != source:
                    return location

        query = doc.text.lower()

        vague_destination_query = any(
            phrase in query
            for phrase in [
                "getaway from",
                "vacation from",
                "holiday from",
                "somewhere",
                "near the coast",
                "near coast",
                "coastal",
                "preferably near",
            ]
        )

        if vague_destination_query:
            return None

        if source:
            return None

        for ent in doc.ents:
            if ent.label_ in {"GPE", "LOC"}:
                value = ent.text.strip().title()

                if value and value != source:
                    return value

        return None

    def _collect_prepositional_object(self, prep_token) -> Optional:
        words = []

        for child in prep_token.children:
            if child.dep_ in {"pobj", "pcomp", "compound"} or child.ent_type_ in {"GPE", "LOC"}:
                subtree_words = [token.text for token in child.subtree]
                words.extend(subtree_words)

        if not words:
            return None

        value = " ".join(words).strip(" ,.")
        value = value.title()

        blocked = {
            "The Coast",
            "Coast",
            "Beach",
            "Beaches",
            "Somewhere",
            "Nearby",
        }

        if value in blocked:
            return None

        return value

    def _extract_entities(self, doc) -> Dict[str, Any]:
        result = {
            "source": None,
            "destination": None,
            "month": None,
            "days": None,
            "travelers": None,
        }

        for ent in doc.ents:
            if ent.label_ == "DATE":
                date_value = self._normalize_date_entity(ent.text)

                if date_value.get("month"):
                    result["month"] = date_value["month"]

                if date_value.get("days"):
                    result["days"] = date_value["days"]

            if ent.label_ == "CARDINAL":
                number = self._safe_int(ent.text)

                if number:
                    nearby_text = self._get_nearby_text(doc, ent.start, ent.end)

                    if any(word in nearby_text for word in ["friend", "friends", "people", "person", "traveler", "travellers", "travelers"]):
                        result["travelers"] = number

                    if any(word in nearby_text for word in ["day", "days", "night", "nights"]):
                        result["days"] = number

        return result

    def _normalize_date_entity(self, text: str) -> Dict[str, Any]:
        value = text.lower()

        month_map = {
            "january": "January",
            "february": "February",
            "march": "March",
            "april": "April",
            "may": "May",
            "june": "June",
            "july": "July",
            "august": "August",
            "september": "September",
            "october": "October",
            "november": "November",
            "december": "December",
            "christmas": "December",
            "new year": "January",
        }

        for key, month in month_map.items():
            if key in value:
                return {"month": month, "days": None}

        if "long weekend" in value:
            return {"month": None, "days": 3}

        if "weekend" in value:
            return {"month": None, "days": 2}

        if "week" in value:
            return {"month": None, "days": 7}

        return {"month": None, "days": None}

    def _extract_interest_candidates(self, doc) -> List:
        interest_labels = {
            "beach": {"beach", "beaches", "coast", "coastal", "sea"},
            "nature": {"nature", "hill", "hills", "mountain", "mountains", "forest", "wildlife", "lake"},
            "food": {"food", "cuisine", "restaurant", "restaurants"},
            "nightlife": {"nightlife", "club", "clubs", "party", "pub", "bar"},
            "relaxation": {"peaceful", "relaxing", "relaxed", "calm", "quiet"},
            "romantic": {"romantic", "couple"},
            "heritage": {"heritage", "history", "historical", "fort", "palace", "museum"},
            "religious": {"temple", "temples", "church", "mosque", "spiritual"},
            "adventure": {"adventure", "trek", "trekking", "rafting", "scuba"},
            "shopping": {"shopping", "market", "markets"},
        }

        found = set()

        lemmas = {token.lemma_.lower() for token in doc if not token.is_stop}
        texts = {token.text.lower() for token in doc if not token.is_stop}
        words = lemmas.union(texts)

        for label, keywords in interest_labels.items():
            if words.intersection(keywords):
                found.add(label)

        return sorted(found)

    def _extract_budget_candidate(self, doc) -> Optional:
        words = [token.text.lower() for token in doc]
        joined = " ".join(words)

        low_phrases = [
            "not too expensive",
            "not expensive",
            "not costly",
            "not too costly",
            "not very expensive",
            "not very costly",
            "affordable",
            "cheap",
            "budget friendly",
            "budget-friendly",
            "pocket friendly",
            "pocket-friendly",
        ]

        for phrase in low_phrases:
            if phrase in joined:
                return "low"

        medium_phrases = [
            "moderate",
            "comfortable",
            "standard",
            "decent",
            "mid range",
            "mid-range",
        ]

        for phrase in medium_phrases:
            if phrase in joined:
                return "medium"

        high_phrases = [
            "luxury",
            "premium",
            "high budget",
            "5 star",
            "five star",
            "lavish",
        ]

        for phrase in high_phrases:
            if phrase in joined:
                return "high"

        if "expensive" in words or "costly" in words:
            return "high"

        return None

    def _is_spacy_result_good_enough(self, request: TripRequest) -> bool:
        query = request.user_query.lower()
    
        if request.source and request.destination:
            if request.source.strip().lower() == request.destination.strip().lower():
                return False
    
        vague_destination_signals = [
            "somewhere",
            "near",
            "nearby",
            "preferably",
            "coastal",
            "near the coast",
            "getaway from",
            "vacation from",
            "holiday from",
            "peaceful",
            "relaxing",
            "romantic",
            "not too",
            "around",
            "new year",
            "christmas",
            "long weekend",
        ]
    
        if any(signal in query for signal in vague_destination_signals):
            return False
    
        if request.confidence < self.confidence_threshold:
            return False
    
        if request.missing_fields:
            return False
    
        return True

    def _analyze_with_gemini(
    self,
    user_query: str,
    spacy_request: TripRequest
) -> Optional:
        if not self.model:
            print("[IntentAnalyzer] Gemini model not initialized. Check GEMINI_API_KEY in .env")
            return None

        prompt = self._build_gemini_prompt(user_query, spacy_request)

        try:
            response = self.model.generate_content(
    prompt,
    generation_config={
        "temperature": 0.1,
        "top_p": 0.8,
        "top_k": 40,
    }
)
            text = response.text.strip()


            json_text = self._extract_json(text)
            data = json.loads(json_text)

            request = TripRequest(
                user_query=user_query,
                source=data.get("source"),
                destination=data.get("destination"),
                month=data.get("month"),
                days=data.get("days"),
                budget=data.get("budget"),
                travelers=data.get("travelers"),
                interests=data.get("interests") or [],
                travel_dates=data.get("travel_dates"),
                suggested_agents=data.get("required_agents") or [],
                missing_fields=data.get("missing_fields") or [],
                confidence=float(data.get("confidence", 0.85)),
                parser_used="gemini",
            )

            request.suggested_agents = self._validate_agents(
                request.suggested_agents,
                request
            )

            return request

        except Exception as e:
            print("[IntentAnalyzer] Gemini intent analysis failed:")
            print(type(e).__name__, str(e))
            return None

    def _build_gemini_prompt(self, user_query: str, spacy_request: TripRequest) -> str:
        spacy_json = {
        "source": spacy_request.source,
        "destination": spacy_request.destination,
        "month": spacy_request.month,
        "days": spacy_request.days,
        "budget": spacy_request.budget,
        "travelers": spacy_request.travelers,
        "interests": spacy_request.interests,
        "suggested_agents": spacy_request.suggested_agents,
        "missing_fields": spacy_request.missing_fields,
        "confidence": spacy_request.confidence,
    }

        return f"""
You are a strict JSON intent analyzer for a dynamic multi-agent trip planning system.

Return only valid JSON.
Do not include markdown.
Do not explain anything.
Do not add comments.

Allowed agents:
- destination_agent
- climate_agent
- transport_agent
- hotel_agent
- itinerary_agent
- budget_agent

Your task:
Extract the user's travel intent.

Important interpretation rules:
1. Do not invent a destination if the user has not explicitly provided one.
2. If the user says "somewhere", "near the coast", "mountains", "nature", "peaceful place", "romantic place", or similar preference-based wording, keep destination as null.
3. If destination is null, include destination_agent.
4. Do not include transport_agent unless both source and destination are available.
5. If this is a full trip, vacation, holiday, getaway, or itinerary request, include:
   destination_agent, climate_agent, hotel_agent, itinerary_agent, budget_agent.
6. If both source and destination are available, include transport_agent.
7. If the user gives a date range like "6-7 day trip", set days to the lower number, e.g. 6.
8. If the user says "long weekend", set days to 3.
9. If the user says "weekend", set days to 2.
10. If the user says "week", set days to 7.
11. If the user says "parents and I", set travelers to 3.
12. If the user says "my wife and I", "my husband and I", or "couple", set travelers to 2.
13. If the user says "family" but no number is given, set travelers to 4.
14. If the user says "friends" with a number, use that number.
15. Map Christmas to December.
16. Map New Year to January unless the user clearly says New Year's Eve, then use December.
17. If the user says "after Diwali" and no exact date/year is provided, keep month as null.
18. Budget mapping:
    - "cheap", "budget", "affordable", "not too expensive", "not costly" -> low
    - "luxury", "premium", "5 star", "lavish" -> high
    - "comfortable", "decent", "moderate", "not luxury but not too cheap", "not too cheap", "mid range" -> medium
19. Interests must be simple labels only:
    beach, nature, food, nightlife, heritage, religious, adventure, shopping, relaxation, romantic
20. If a field cannot be inferred confidently, use null.
21. confidence should reflect the final extracted intent, between 0 and 1.
If destination is a broad state/region like Rajasthan, Kerala, Himachal, Odisha, South India, North East, set destination_scope = "state_or_region".
If destination is a specific city/town like Jaipur, Ooty, Goa, Munnar, Udaipur, set destination_scope = "city".
If no destination is provided, set destination_scope = "unknown".
If destination_scope is "state_or_region", do not include climate_agent, transport_agent, hotel_agent, or itinerary_agent yet. Include destination_agent and budget_agent only.

Example 1:
User: We are 3 friends looking for a relaxing but fun long weekend getaway from Pune sometime around New Year, preferably near the coast, with good food, some nightlife, and not too costly.
Output:
{{
  "source": "Pune",
  "destination": null,
  "month": "January",
  "days": 3,
  "budget": "low",
  "travelers": 3,
  "interests": ["beach", "food", "nightlife", "relaxation"],
  "travel_dates": null,
  "required_agents": ["destination_agent", "climate_agent", "hotel_agent", "itinerary_agent", "budget_agent"],
  "missing_fields": ["destination"],
  "confidence": 0.85
}}

Example 2:
User: My parents and I want a calm 6-7 day trip sometime after Diwali from Hyderabad, preferably somewhere with mountains or nature, comfortable stays, easy travel, not luxury but not too cheap either.
Output:
{{
  "source": "Hyderabad",
  "destination": null,
  "month": null,
  "days": 6,
  "budget": "medium",
  "travelers": 3,
  "interests": ["nature", "relaxation"],
  "travel_dates": null,
  "required_agents": ["destination_agent", "climate_agent", "hotel_agent", "itinerary_agent", "budget_agent"],
  "missing_fields": ["destination", "month"],
  "confidence": 0.85
}}

Now analyze this user query:
{user_query}

spaCy result:
{json.dumps(spacy_json, indent=2)}

Return JSON exactly in this structure:
{{
  "source": null,
  "destination": null,
  "month": null,
  "days": null,
  "budget": null,
  "travelers": null,
  "interests": [],
  "travel_dates": null,
  "required_agents": [],
  "missing_fields": [],
  "confidence": 0.0
}}
"""

    def _extract_json(self, text: str) -> str:
        text = text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()

        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            return text[start:end + 1]

        return text

    def _infer_agents(self, request: TripRequest) -> List:
        agents = []

        if request.destination or not request.destination:
            agents.append(AGENT_DESTINATION)

        if request.month:
            agents.append(AGENT_CLIMATE)

        if request.source and request.destination:
            agents.append(AGENT_TRANSPORT)

        if request.destination or request.budget:
            agents.append(AGENT_HOTEL)

        if request.destination or request.days:
            agents.append(AGENT_ITINERARY)

        if request.budget or request.days or request.travelers:
            agents.append(AGENT_BUDGET)

        return self._validate_agents(agents, request)

    def _validate_agents(self, agents: List[str], request: TripRequest) -> List:
        preferred_order = [
            AGENT_DESTINATION,
            AGENT_CLIMATE,
            AGENT_TRANSPORT,
            AGENT_HOTEL,
            AGENT_ITINERARY,
            AGENT_BUDGET,
        ]

        valid_agents = set(preferred_order)
        ordered = []

        for agent in preferred_order:
            if agent in agents and agent in valid_agents and agent not in ordered:
                ordered.append(agent)

        if AGENT_TRANSPORT in ordered:
            if not request.source or not request.destination:
                ordered.remove(AGENT_TRANSPORT)

        return ordered

    def _find_missing_fields(self, request: TripRequest) -> List:
        missing = []

        if not request.destination:
            missing.append("destination")

        return missing

    def _score_spacy_result(self, request: TripRequest) -> float:
        score = 0.0

        if request.source:
            score += 0.15

        if request.destination:
            score += 0.25

        if request.month:
            score += 0.15

        if request.days:
            score += 0.10

        if request.travelers:
            score += 0.10

        if request.budget:
            score += 0.10

        if request.interests:
            score += 0.10

        if request.suggested_agents:
            score += 0.05

        return round(min(score, 1.0), 2)

    def _safe_int(self, value: str) -> Optional:
        try:
            return int(value)
        except Exception:
            return None

    def _get_nearby_text(self, doc, start: int, end: int, window: int = 3) -> str:
        left = max(0, start - window)
        right = min(len(doc), end + window)

        return " ".join(token.text.lower() for token in doc[left:right])