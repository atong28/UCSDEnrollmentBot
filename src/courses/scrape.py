import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import json
from urllib.parse import urljoin
import os
from datetime import datetime, timedelta as td

from ..const import ALPHABET

def scrape(url):
    '''
    Scrape course listing page for given link.
    '''
    print(f"Loading {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    courses = defaultdict(list)

    for course in soup.find_all("p", class_="course-name"):
        dept = ''
        for i, c in enumerate(course.text):
            if c == ' ' and course.text[i+1].isnumeric(): break
            dept += c
        if '(' in dept:
            dept = dept.split('(')[1].split(')')[0]
        course_code = dept + ' '
        i += 1
        for i, c in enumerate(course.text[i:], start=i):
            if c == ' ': break
            course_code += c if c != '.' else ''
        i += 1
        title = course.text[i:].strip().split('(')
        if len(title) == 1:
            title = title[0]
            units = None
        else:
            units = title[-1].split(')')[0]
            title = '('.join(title[:-1]).strip()
        course_desc = course.find_next("p")
        if not course_desc:
            print(f'{course_code} has no description')
            continue
        course_desc = course_desc.text.strip()
        
        if "Prerequisite" in course_desc:
            prereqs = course_desc.split("Prerequisites:")[1].strip()
        else:
            prereqs = "None"
        for subdept in dept.split('/'):
            courses[subdept].append({
                "code": course_code,
                "title": title,
                "units": units,
                "desc": course_desc,
                "prereqs": prereqs
            })
    for subdept in courses:
        with open(f'data/courses/{subdept}.json', 'w', encoding='utf-8') as f:
            json.dump(courses[subdept], f, indent=4)

def scrape_enrollment_calendar(year: int):
    url = f'https://blink.ucsd.edu/instructors/courses/enrollment/calendars/20{year}.html'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    data = {
        f'FA{year}': {},
        f'WI{year+1}': {},
        f'SP{year+1}': {},
        f'SU{year+1}': {}
    }
    for row in soup.find('table').find_all('tr')[1:]:
        entry = row.find('td')
        if entry.text.strip().startswith('Enrollment begins'):
            fall = entry.find_next('td')
            winter = fall.find_next('td')
            spring = winter.find_next('td')
            summer = spring.find_next('td')
            for qtr, start in zip(data, (fall, winter, spring, summer)):
                if '/' not in start.text:
                    continue
                m, d = fall.text.strip().split('/')
                start = datetime(2000 + year, int(m), int(d), 8)
                data[qtr]['fp4'] = (start, start + td(days=3))
                data[qtr]['fp3'] = (start + td(days=3), start + td(days=4))
                data[qtr]['fp2'] = (start + td(days=4), start + td(days=5))
                data[qtr]['fp1'] = (start + td(days=5), start + td(days=6))
        if entry.text.strip().startswith('Wait Lists'):
            fall = entry.find_next('td')
            winter = fall.find_next('td')
            spring = winter.find_next('td')
            summer = spring.find_next('td')
            for qtr, start in zip(data, (fall, winter, spring, summer)):
                if '/' not in start.text:
                    continue
                m, d = start.text.strip().split('/')
                start = datetime(2000 + year, int(m), int(d), 8)
                data[qtr]['sp4'] = (start, start + td(days=3))
                data[qtr]['sp3'] = (start + td(days=3), start + td(days=4))
                data[qtr]['sp2'] = (start + td(days=4), start + td(days=5))
                data[qtr]['sp1'] = (start + td(days=5), start + td(days=6))
        if entry.text.strip().startswith('New undergraduate student'):
            m, d = entry.find_next('td').text.strip().split('/')
            start = datetime(2000 + year, int(m), int(d), 8)
            data[f'FA{year}']['fpt'] = (start, start + td(days=1))
            data[f'FA{year}']['fpf'] = (start + td(days=1), start + td(days=4, hours=16))
            data[f'FA{year}']['spt'] = (start + td(days=5), start + td(days=6))
            data[f'FA{year}']['spf'] = (start + td(days=6), start + td(days=9, hours=16))
    jsonify = lambda x: x.strftime("%Y %m %d %H %M %S")
    data = {name: {k: (jsonify(v[0]), jsonify(v[1])) for k, v in qtr.items()} for name, qtr in data.items()}
    with open(f'data/enrollment_calendar/{year}.json', 'w') as f:
        json.dump(data, f, indent=4)
    

def scrape_all():
    base_url = "https://catalog.ucsd.edu/front/courses.html"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    course_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        print(href)
        if href.startswith("../courses/"):
            full_url = urljoin(base_url, href)
            course_links.append(full_url)
    print("Found course links:", course_links)
    for link in course_links:
        scrape(link)
    
    # remove marine biology conservation grad electives that is not a class    
    os.remove('data/courses/12.json')