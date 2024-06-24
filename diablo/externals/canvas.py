"""
Copyright ©2024. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""
import re

from canvasapi import Canvas
from canvasapi.external_tool import ExternalTool
from canvasapi.user import User
from diablo import skip_when_pytest
from diablo.lib.berkeley import get_canvas_sis_term_id
from diablo.lib.util import resolve_xml_template
from flask import current_app as app
import requests


def get_account():
    c = _get_canvas()
    return c.get_account(app.config['CANVAS_BERKELEY_ACCOUNT_ID'])


@skip_when_pytest(mock_object='canvas/canvas_course_sites.json', is_fixture_json_file=True)
def get_canvas_course_sites(canvas_enrollment_term_id):
    canvas_courses = get_account().get_courses(
        by_subaccounts=app.config['CANVAS_BERKELEY_SUB_ACCOUNTS'],
        enrollment_term_id=canvas_enrollment_term_id,
    )
    course_sites_by_id = {}
    # Sample formats: 'SEC:2020-B-21662', 'SEC:2020-B-21662-9F6ED069'
    sis_section_regex = re.compile(r'SEC:\d+-\D-(\d+).*')
    for canvas_course in canvas_courses:
        for section in canvas_course.get_sections():
            if hasattr(section, 'course_id') and hasattr(section, 'sis_section_id'):
                course_site_id = section.course_id
                sis_section_id = section.sis_section_id
                section_id = sis_section_regex.search(sis_section_id).group(1) if sis_section_id else None
                if section_id:
                    if course_site_id not in course_sites_by_id:
                        course_sites_by_id[course_site_id] = {
                            'id': course_site_id,
                            'name': canvas_course.name,
                            'section_ids': set(),
                        }
                    course_sites_by_id[course_site_id]['section_ids'].add(section_id)
    return list(course_sites_by_id.values())


@skip_when_pytest(mock_object=type('EnrollmentTerm', (object,), {'id': 9999}))
def get_canvas_enrollment_term(sis_term_id):
    canvas_sis_term_id = get_canvas_sis_term_id(sis_term_id)
    canvas_enrollment_term = None
    for enrollment_term in get_account().get_enrollment_terms():
        if enrollment_term.sis_term_id == canvas_sis_term_id:
            canvas_enrollment_term = enrollment_term
            break
    return canvas_enrollment_term


def get_user(user_id, api_call=True, api_url=None):
    c = _get_canvas()
    if api_call is False:
        return User(c._Canvas__requester, {'id': user_id})
    else:
        user = None
        try:
            user = c.get_user(user_id)
        except Exception as e:
            app.logger.error(f'Failed to retrieve Canvas user (id={user_id})')
            app.logger.exception(e)
        return user


def get_teaching_courses(uid):
    teaching_courses = []
    try:
        user = get_user(f'sis_login_id:{uid}', api_call=False)
        profile = user.get_profile()
        if profile:
            # Load all courses because ResourceDoesNotExist is possible when paging.
            courses = [course for course in user.get_courses(include=['term'])]
            for canvas_course in courses:
                enrollments = list(filter(lambda e: e.get('user_id') == profile['id'], canvas_course.enrollments))
                current_user_roles = [e['role'] for e in enrollments]
                if next((role for role in current_user_roles if role in ['TeacherEnrollment', 'CanvasAdmin']), None):
                    teaching_courses.append(_canvas_site_to_api_json(canvas_course))
    except Exception as e:
        app.logger.error(f'Failed to retrieve courses which UID {uid} is currently teaching.')
        app.logger.exception(e)

    # Sort order: current-term sites, then termless sites (including project sites), then past terms descending.
    def _sort_key(canvas_site):
        if canvas_site['sisTermId'] == app.config['CURRENT_TERM_ID']:
            return 'Z'
        elif canvas_site['sisTermId'] == 'TERM:Projects' or not canvas_site['sisTermId']:
            return 'Y'
        else:
            return canvas_site['sisTermId']

    return sorted(teaching_courses, key=_sort_key, reverse=True)


def ping_canvas(timeout):
    url = f"{app.config['CANVAS_API_URL']}/accounts/{app.config['CANVAS_BERKELEY_ACCOUNT_ID']}"
    headers = {'Authorization': f"Bearer {app.config['CANVAS_ACCESS_TOKEN']}"}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        return bool(response and response.status_code == 200)
    except Exception:
        return False


def update_lti_configurations():
    canvas = _get_canvas()
    successes = []
    errors = []
    for tool_name, tool_id in app.config.get('CANVAS_LTI_EXTERNAL_TOOL_IDS', {}).items():
        xml_string = resolve_xml_template(f'{tool_name}.xml')
        external_tool = ExternalTool(
            canvas._Canvas__requester,
            {
                'account_id': app.config['CANVAS_BERKELEY_ACCOUNT_ID'],
                'id': tool_id,
            },
        )
        response = None
        try:
            response = external_tool.edit(
                config_type='by_xml',
                config_xml=xml_string,
                consumer_key=app.config['CANVAS_LTI_KEY'],
                shared_secret=app.config['CANVAS_LTI_SECRET'],
            )
        except Exception as e:
            app.logger.error(f'Failed to update external tool {tool_name} due to error: {str(e)}')
            app.logger.exception(e)
        if response and response.name:
            successes.append(response.name)
        else:
            errors.append(tool_name)
    return successes, errors


def _canvas_site_to_api_json(canvas_site):
    return {
        'canvasSiteId': canvas_site.id,
        'courseCode': canvas_site.course_code,
        'name': canvas_site.name.strip(),
        'sisCourseId': canvas_site.sis_course_id,
        'sisTermId': canvas_site.term['sis_term_id'],
        'url': f"{app.config['CANVAS_API_URL']}/courses/{canvas_site.id}",
    }


def _get_canvas():
    return Canvas(
        base_url=app.config['CANVAS_API_URL'],
        access_token=app.config['CANVAS_ACCESS_TOKEN'],
    )
