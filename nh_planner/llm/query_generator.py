import json
import logging
import re
from typing import Optional

LOGGER = logging.getLogger(__name__)


def process_json(json_str: str) -> Optional[list[dict]]:
    json_list = json.loads(json_str)
    if not isinstance(json_list, list):
        return None
    return json_list


class QueryGenerator:
    def __init__(self):
        pass

    def validate_query(self, query: str) -> bool:
        query_upper = query.upper()
        if not query_upper.strip().startswith("SELECT"):
            return False
        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"]
        if any(keyword in query_upper for keyword in dangerous_keywords):
            return False
        return True

    def extract_reasoning_plan(self, llm_response: str) -> Optional[List[Dict]]:
        """Extract a multi-step reasoning plan from LLM response"""
        try:
            if "```json" in llm_response:
                match = re.search(r"```json\n(.*?)\n```", llm_response, re.DOTALL)
                if match:
                    return process_json(match.group(1))
            else:
                return process_json(llm_response)
        except json.JSONDecodeError as e:
            logging.exception("Failed to extract reasoning, invalid JSON {}".format(e))
            return None

    def extract_query(self, llm_response: str) -> Optional[str]:
        """Extract SQL query from LLM response"""
        if "```sql" not in llm_response:
            query = llm_response
        else:
            query = (
                re.search(r"```sql\n(.*?)\n```", llm_response, re.DOTALL)
                .group(1)
                .strip()
            )
        if query:
            if self.validate_query(query):
                return query
        return None
