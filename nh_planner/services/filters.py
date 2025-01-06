from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MovieFilter(BaseModel):
    title: Optional[str] = None
    director: Optional[str] = None
    min_duration: Optional[int] = Field(None)
    max_duration: Optional[int] = Field(None)
    start_date: str = Field(default=datetime.now().strftime("%Y-%m-%d %H:%M"))
    end_date: Optional[str] = None

    def to_sql(self) -> tuple[str, list]:
        conditions = ["1=1"]
        params = []

        if self.title:
            conditions.append("LOWER(m.title) LIKE LOWER(?)")
            params.append(f"%{self.title}%")

        if self.director:
            conditions.append("LOWER(m.director) LIKE LOWER(?)")
            params.append(f"%{self.director}%")

        if self.min_duration:
            conditions.append("m.duration >= ?")
            params.append(self.min_duration)

        if self.max_duration:
            conditions.append("m.duration <= ?")
            params.append(self.max_duration)

        if self.start_date:
            conditions.append("s.screening_date >= ?")
            params.append(self.start_date)

        if self.end_date:
            conditions.append("s.screening_date <= ?")
            params.append(self.end_date)

        return " AND ".join(conditions), params
