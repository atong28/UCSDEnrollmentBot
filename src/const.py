print('[Initialization] Loading files...')
from datetime import datetime
import os
import re

from sentence_transformers import SentenceTransformer
import faiss
import discord

from .utils import read_json

__all__ = ['MODEL', 'COURSES', 'INDEX', 'YEAR', 'ENROLLMENT_TIMES', 'ALPHABET', 'ALLOWED_TAGS', 
           'ALLOWED_ATTRIBUTES', 'SEARCH_FILTERS']

TOKEN = read_json('data/config/bot.json')['token']

MODEL = SentenceTransformer('all-MiniLM-L6-v2')
COURSES = []
for dept in os.listdir('data/courses'):
    COURSES.extend(read_json(f'data/courses/{dept}'))
INDEX = faiss.read_index("data/course_catalog.faiss")

YEAR = read_json('data/config/year.json')['year']
_times = read_json(f'data/enrollment_calendar/{YEAR}.json')
ENROLLMENT_TIMES = {
    qtr: {
        k: (datetime(*map(int, v[0].split(' '))), datetime(*map(int, v[1].split(' '))))
        for k, v in times.items()
    } for qtr, times in _times.items()
}
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

ALLOWED_TAGS = ['b', 'i', 'u', 'strong', 'em', 'p', 'a', 'ul', 'ol', 'li', 'br', 'h1', 'h2', 'h3',
                'h4', 'h5', 'h6', 'div', 'table', 'tr', 'td', 'span', 'tbody']
ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id'],
    'a': ['href', 'title'],
    'span': ['department', 'number']
}

SEARCH_FILTERS = {
    "Lower Division": re.compile(r"[A-Z]{2,4} ([0-9]{1,2}[A-Za-z]*)\b"),
    "Upper Division": re.compile(r"[A-Z]{2,4} (1[0-9]{2}[A-Za-z]*)\b"),
    "Graduate": re.compile(r"[A-Z]{2,4} ([2-9][0-9]{2,}[A-Za-z]*)\b"),
    "Undergraduate": re.compile(r"([A-Z]{2,4} ([0-9]{1,2}[A-Za-z]*)\b)|([A-Z]{2,4} (1[0-9]{2}[A-Za-z]*)\b)"),
    "All Courses": re.compile(r".*")
}

BOT = discord.Bot(debug_guilds=[1307184534336442459])
print('[Initialization] Done!')