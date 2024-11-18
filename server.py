import re
import os

from flask import Flask, request, jsonify
from flask_cors import CORS
import bleach
from bs4 import BeautifulSoup

from src.db import insert_or_update_user
from src.const import ALLOWED_TAGS, ALLOWED_ATTRIBUTES

app = Flask(__name__)
CORS(app, resources={r"/degree_audit_post": {"origins": "https://act.ucsd.edu"}})

def process_audit(html: str):
    soup = BeautifulSoup(html, 'html.parser')
    for br_tag in soup.find_all('br'):
        br_tag.insert_before('\n')
        br_tag.decompose()
    audit = {}
    
    # find pid
    pid_div = [result for result in soup.find_all('div', class_='auditHeaderEntryLabel col-1') if 'PID' in result.text]
    if not pid_div:
        return -1

    next_div = pid_div[0].find_next_sibling('div')
    pid = next_div.text.strip()
    audit['pid'] = pid
    
    unit_totals = soup.find('div', class_='category_Overall_Hrs')
    if not unit_totals:
        return -1
    earned_units = 0
    wip_units = 0
    if (earned := unit_totals.find('tr', class_='reqEarned')):
        earned_units = float(earned.find('span', class_=['hours', 'number']).text.strip())
    if (wip := unit_totals.find('tr', class_='reqIpDetail')):
        wip_units = float(wip.find('span', class_=['hours', 'number']).text.strip())
    audit['earned_units'] = earned_units
    audit['wip_units'] = wip_units
    
    def normalize_code(code: str):
        for i, c in enumerate(code):
            if c.isdigit():
                return code[:i].strip() + ' ' + code[i:].strip()
            
    def extract_major_categories(categories: list):
        major_reqs = []
        for major_category in categories:
            major_category_dict = {}
            major_category_dict['major_category'] = major_category.find('div', class_='reqTitle').text.strip()
            major_category_dict['subreqs'] = []
            subreqs = major_category.find_all('div', class_='subrequirement')
            for subreq in subreqs:
                if (title := subreq.find('span', class_='subreqTitle')):
                    title = title.text
                else:
                    title = 'Failed to load title :('
                
                subreq_dict = {
                    'title': ' '.join(title.strip().split()),
                    'progress': {
                        'type': 'complete',
                        'remaining': 0
                    },
                    'completed_courses': [],
                    'needed_courses': []
                }
                subreq_needs = subreq.find('table', class_='subreqNeeds')
                if subreq_needs:
                    units_left = subreq_needs.find('td', class_='hours')
                    if units_left:
                        subreq_dict['progress']['type'] = 'units'
                        subreq_dict['progress']['remaining'] = float(units_left.text.strip())
                    courses_left = subreq_needs.find('td', class_='count')
                    if courses_left:
                        subreq_dict['progress']['type'] = 'courses'
                        subreq_dict['progress']['remaining'] = int(courses_left.text.strip())
                
                completed_courses = subreq.find_all('tr', class_='takenCourse')
                completed_courses = [normalize_code(course.find('td', class_='course').text) for course in completed_courses]
                subreq_dict['completed_courses'] = completed_courses
                needed_courses = subreq.find_all(lambda tag: 'course' in tag.get('class', []) and 'draggable' in tag.get('class', []))
                needed_courses = [
                    f'{course.get('department').strip()} {course.get('number').strip()}'
                    for course in needed_courses
                ]
                subreq_dict['needed_courses'] = needed_courses
                major_category_dict['subreqs'].append(subreq_dict)
            major_reqs.append(major_category_dict)
        return major_reqs
    sections = soup.find_all(lambda tag: 'requirement' in tag.get('class', []) and 'Status_NONE' in tag.get('class', []) and 'category_Zap/don\'t_grph' in tag.get('class', []))
    major_categories = soup.find_all('div', class_='category_Major')
    if major_categories:
        audit['major'] = {}
        audit['major']['title'] = sections[0].find('div', class_='reqHeader').text.strip()
        audit['major']['categories'] = extract_major_categories(major_categories)

    second_major_categories = soup.find_all('div', class_='category_Second_Major')
    if second_major_categories:
        audit['second_major'] = {}
        audit['second_major']['title'] = sections[1].find('div', class_='reqHeader').text.strip()
        audit['second_major']['categories'] = extract_major_categories(second_major_categories)
    
    return audit
    

@app.route('/degree_audit_post', methods=['POST'])
def receive_audit():
    if not request.is_json:
        return jsonify({"error": "Invalid request. Expected JSON data."}), 400
    
    data = request.get_json()
    html_content = data.get('html')
    
    if not html_content:
        return jsonify({"error": "No HTML content provided."}), 400
    sanitized_html = bleach.clean(html_content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    sanitized_html = re.sub(r"&lt;.*?&gt;", "", sanitized_html)
    try:
        processed_audit = process_audit(sanitized_html)
    except AttributeError:
        next_id = 0
        while os.path.exists(f'data/failed_audits/{next_id}.html'):
            next_id += 1
        with open(f'data/failed_audits/{next_id}.html', 'w') as f:
            f.write(sanitized_html)
            
    if processed_audit == -1:
        return jsonify({"error": "Invalid degree audit!"}), 400

    insert_or_update_user(processed_audit['pid'], processed_audit)
    return jsonify({"message": "Degree audit received successfully!"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)