# nh-planner (in progress)

A CLI app that enables to scrape the screenings of Nowe Horyzonty cinema ([NH](https://www.kinonh.pl/index.s)) and then to filter the data.


![media/screenshot.png](media/screenshot.png)

## About

```
├── LICENSE
├── README.md
├── media
│   └── screenshot.png
├── nh_planner
│   ├── __init__.py
│   ├── cli
│   │   ├── __init__.py
│   │   ├── app.py
│   │   └── utils.py
│   ├── config.py
│   ├── db
│   │   ├── __init__.py
│   │   ├── data_models.py
│   │   ├── database.py
│   │   ├── dynamic_scrapper.py
│   │   ├── queries.py
│   │   └── utils.py
│   ├── llm
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── conversation.py
│   │   ├── llm.py
│   │   ├── query_generator.py
│   │   └── reasoning.py
│   └── main.py
├── pyproject.toml
└── uv.lock
```

## Installation

