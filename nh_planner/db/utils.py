from typing import Optional

from pydantic import BaseModel, Field


class TitleFilter(BaseModel):
    title: list[str]


class DurationFilter(BaseModel):
    min_duration: Optional[int] = Field(None)
    max_duration: Optional[int] = Field(None)


class DateFilter(BaseModel):
    start_date: str
    end_date: Optional[str] = Field(None)


class Filter(BaseModel):
    title: Optional[TitleFilter] = Field(None)
    duration: Optional[DurationFilter] = Field(None)
    date: DateFilter


def build_filter_query(filters: Filter) -> str:
    nested_query = """
    SELECT m.id, ms.screening_date FROM movies m JOIN movies_screenings ms ON m.id = ms.movie_id
    """
    nested_conditions = []
    if date_filter := filters.date:
        if date_filter.start_date:
            nested_conditions.append(f"ms.screening_date >= '{date_filter.start_date}'")
        if date_filter.end_date:
            nested_conditions.append(f"ms.screening_date <= '{date_filter.end_date}'")
    if nested_conditions:
        nested_query += " WHERE " + " AND ".join(nested_conditions)
    nested_query += " ORDER BY ms.screening_date"

    query = f"""
    SELECT title, duration, director, genre, production, GROUP_CONCAT(screening_date, '\n') as screening_dates, href
    FROM ({nested_query}) t join movies m on t.id = m.id
    """
    conditions = []
    if title_filter := filters.title:
        titles_where_clause = (
            "("
            + " OR ".join(
                [f"levenshtein(title, '{title}') < 3" for title in title_filter.title]
            )
            + ")"
        )
        conditions.append(titles_where_clause)
    if duration_filter := filters.duration:
        if duration_filter.min_duration:
            conditions.append(f"duration >= {duration_filter.min_duration}")
        if duration_filter.max_duration:
            conditions.append(f"duration <= {duration_filter.max_duration}")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY title, duration, director, genre, production, href"
    return query


def create_levenshtein_function(conn):
    def levenshtein(s1, s2):
        if not s1:
            return len(s2)
        if not s2:
            return len(s1)

        s1, s2 = s1.lower(), s2.lower()
        previous_row = range(len(s2) + 1)

        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    conn.create_function("levenshtein", 2, levenshtein)
