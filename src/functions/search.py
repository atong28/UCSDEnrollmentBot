from ..courses.embed import query
from ..const import SEARCH_FILTERS, COURSES

def search(
    numbers: str = '',
    keywords: str = '',
    dept: str = '',
    division: str = ''
) -> list:
    courses = query(keywords) if keywords else COURSES
    if numbers:
        code_cleaned = [code.strip().upper() for code in numbers.split(',')]
        courses = [course for course in courses if course['code'] in code_cleaned]
    courses = [course for course in courses if SEARCH_FILTERS[division].match(course['code'])]
    if dept:
        courses = [course for course in courses if course['code'].startswith(dept.strip().upper())]