from ollama import ChatResponse, chat
from src.db import execute_sql_query

SQL_QUERY_GENERATOR_PROMPT = """
    Given these SQL tables:
    - movies (id, title, duration, director, genre, production, description)
    - movies_screenings (id, movie_id, screening_date)

    screening_date is a string in the format "YYYY-MM-DD HH:MM", so for example use comparisons like:
    - screening_date > "2022-12-31 12:30", date(screening_date) = '2024-11-30', etc
    
    Generate a SQL query for the following question: {user_query}
    Only use the tables and columns shown above.
    Return only the SQL query without any explanation.
"""


RECOMMENDATIONS_PROMPT = """
    Given these movie screening results: {results}
    Provide a natural language response to the user's question: {user_query}
    Make the response conversational and highlight any relevant details about the movies.
"""


def generate_sql_query(user_query: str) -> str:
    response: ChatResponse = chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": SQL_QUERY_GENERATOR_PROMPT.format(user_query=user_query),
            },
        ],
    )
    return response.message.content


def recommend_movies(user_query: str) -> None:
    sql_query = generate_sql_query(user_query)
    print(f"SQL query for the question: {sql_query}")
    results = execute_sql_query(sql_query)
    stream = chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": RECOMMENDATIONS_PROMPT.format(
                    results=results, user_query=user_query
                ),
            },
        ],
        stream=True,
    )
    for chunk in stream:
        print(chunk["message"]["content"], end="", flush=True)


if __name__ == "__main__":
    user_query = (
        "Show the title and genre of all movies that are longer than 120 minutes."
    )
    sql_query = generate_sql_query(user_query)
    print(f"SQL query for the question: {sql_query}")
    execute_sql_query(sql_query)

    user_query = "What are the movies playing on the 31th of December? I am looking for something with action"
    recommend_movies(user_query)
