"""Curated labeled examples for the local question-intent classifier."""

from __future__ import annotations

INTENT_EXAMPLES: dict[str, list[str]] = {
    "ranking": [
        "which cities have the most jobs",
        "show the top companies by posting count",
        "where are the most entry level openings",
        "rank states by job volume",
        "which employers posted the most roles",
        "top locations for internships",
        "what roles appear most often",
        "list the ten busiest hiring companies",
    ],
    "count": [
        "how many postings are there",
        "count remote jobs",
        "how many entry level positions",
        "number of jobs in Seattle",
        "total internship listings",
        "how many companies are represented",
    ],
    "salary_average": [
        "what is the average salary",
        "average pay by work mode",
        "mean salary for remote jobs",
        "compare average salaries across experience levels",
        "which city has the highest average salary",
    ],
    "salary_median": [
        "what is the median salary",
        "median salary by experience level",
        "which companies have the highest median pay",
        "compare median salary for remote and onsite jobs",
        "median salary range for entry level roles",
    ],
    "percentage": [
        "what percentage of jobs are remote",
        "percentage without salary",
        "share of postings that are internships",
        "what fraction of jobs disclose pay",
        "percent of listings in Maryland",
    ],
    "trend": [
        "how did postings change over time",
        "show the monthly job trend",
        "posting volume by month",
        "are listings increasing over time",
        "time series of job posts",
    ],
    "comparison": [
        "compare remote hybrid and onsite jobs",
        "compare salaries across work modes",
        "entry level versus internship openings",
        "which role has better salary coverage",
        "compare locations by posting volume",
    ],
    "skill_frequency": [
        "what skills appear most often",
        "top skills for remote jobs",
        "most requested skills for data analysts",
        "which technologies are common in engineering listings",
        "rank required skills",
        "skills employers ask for most",
    ],
    "data_quality": [
        "how complete is the dataset",
        "show missing values",
        "are there duplicate rows",
        "what data quality problems exist",
        "how many salaries are missing",
        "is the dataset reliable",
    ],
    "unsupported": [
        "which company has the happiest employees",
        "which job guarantees I get hired",
        "predict next year's job market",
        "which employer is the best place to work",
        "who should I vote for",
        "which race gets hired most",
        "tell me what company culture is like",
    ],
}

SUPPORTED_DEMO_QUESTIONS = [
    "Which cities have the most entry-level job postings?",
    "What are the ten most requested skills for remote jobs?",
    "Which companies have the most internship opportunities?",
    "What is the median salary range by experience level?",
    "How does estimated salary compare between remote, hybrid, and on-site jobs?",
    "What percentage of postings do not disclose salary?",
    "How has job-posting volume changed over time?",
    "Which skills appear most often in electrical engineering and embedded-systems roles?",
    "Which states have the highest number of entry-level engineering jobs?",
    "Which companies have the highest median salary among companies with at least five postings?",
]

UNSUPPORTED_DEMO_QUESTIONS = [
    "Which company has the happiest employees?",
    "Which job will guarantee that I get hired?",
]
