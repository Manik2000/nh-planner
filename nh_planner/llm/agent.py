import json
from typing import Dict, List, Optional

import requests
from ollama import chat, generate

from nh_planner.db.database import DatabaseManager
from nh_planner.llm.conversation import ConversationManager
from nh_planner.llm.query_generator import QueryGenerator
from nh_planner.llm.reasoning import ReasoningChain, ReasoningStep


class LLMAgent:
    def __init__(
        self,
        model_name: str = "llama3.2",
        db_manager: DatabaseManager = DatabaseManager(),
    ):
        self.model_name = model_name
        self.db_manager = db_manager
        self.conversation_manager = ConversationManager()
        self.query_generator = QueryGenerator()

    def generate_planning_prompt(self, user_input: str) -> str:
        """Generate a prompt for the planning phase"""
        context = self.conversation_manager.get_context()
        return f"""
        Previous context: {context}
        Current question: {user_input}
        
        Please create a step-by-step plan to answer this question. For each step, specify:
        1. What information we need to gather
        2. The SQL query to get this information (if needed)
        3. How this information will help answer the question
        
        Format your response as a JSON array of steps, where each step has:
        - description: what we're trying to find out
        - sql_query: the SQL query (if needed)
        
        Example format:
        ```json
        [
            {{
                "description": "Get all movies showing this week",
                "sql_query": "SELECT DISTINCT movies.title FROM movies JOIN screenings ON movies.id = screenings.movie_id WHERE screenings.datetime BETWEEN DATE('now') AND DATE('now', '+7 days')"
            }},
            {{
                "description": "Analyze the results and provide recommendations",
                "sql_query": null
            }}
        ]
        ```
        
        Response should be just the JSON, no additional text.
        """

    def generate_execution_prompt(
        self, step: ReasoningStep, chain: ReasoningChain
    ) -> str:
        """Generate a prompt for executing a specific step"""
        return f"""
        Previous steps and results:
        {chain.get_summary()}
        
        Current step: {step.description}
        
        Please analyze the results and provide the next steps or final answer.
        If you need more information, provide it in the following format:
        ```sql
        YOUR_SQL_QUERY_HERE
        ```
        
        If this is the final step, provide a clear, natural language response.
        """

    def get_llm_response(self, prompt: str) -> str:
        """Get response from Ollama API"""
        return generate(model=self.model_name, prompt=prompt)["response"]

    def execute_reasoning_step(self, step: ReasoningStep) -> None:
        """Execute a single reasoning step"""
        if step.sql_query:
            try:
                results = self.db_manager.execute_query(step.sql_query)
                results_str = json.dumps([dict(row) for row in results], indent=2)
                step.result = results_str
            except Exception as e:
                step.error = str(e)

    def process_user_input(self, user_input: str) -> Dict:
        """Process user input with multi-step reasoning"""
        planning_prompt = self.generate_planning_prompt(user_input)
        plan_response = self.get_llm_response(planning_prompt)
        print(plan_response)

        plan = self.query_generator.extract_reasoning_plan(plan_response)
        print(plan)
        if not plan:
            return {"error": "Failed to generate reasoning plan"}

        chain = ReasoningChain()

        for step_data in plan:
            step = ReasoningStep(
                description=step_data["description"],
                sql_query=step_data.get("sql_query"),
            )

            self.execute_reasoning_step(step)
            chain.add_step(step)

            execution_prompt = self.generate_execution_prompt(step, chain)
            step_response = self.get_llm_response(execution_prompt)

            additional_query = self.query_generator.extract_query(step_response)
            if additional_query:
                additional_step = ReasoningStep(
                    description="Additional information needed",
                    sql_query=additional_query,
                )
                self.execute_reasoning_step(additional_step)
                chain.add_step(additional_step)

        self.conversation_manager.add_exchange(user_input, chain.get_summary())

        return {"reasoning_chain": chain, "final_response": step_response}
