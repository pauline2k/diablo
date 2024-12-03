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
import glob
import json

from diablo import cache, db, std_commit
from diablo.factory import background_job_manager
from diablo.jobs.house_keeping_job import HouseKeepingJob
from diablo.jobs.sis_data_refresh_job import SisDataRefreshJob
from diablo.lib.development_db_utils import save_mock_courses
from diablo.lib.util import utc_now
from diablo.models.admin_user import AdminUser
from diablo.models.blackout import Blackout
from diablo.models.email_template import EmailTemplate
from diablo.models.job import Job
from diablo.models.room import Room
from diablo.models.sis_section import SisSection
from flask import current_app as app
from sqlalchemy.sql import text
from tests.util import simply_yield

_test_users = [
    {
        'uid': '90001',
        'deleted_at': None,
    },
    {
        'uid': '90002',
        'deleted_at': utc_now(),
    },
]


def clear():
    with open(app.config['BASE_DIR'] + '/scripts/db/drop_schema.sql', 'r') as ddlfile:
        db.session().execute(text(ddlfile.read()))
        std_commit()


def load(create_test_data=True):
    cache.clear()
    _load_schemas()
    if create_test_data:
        _create_blackouts()
        _create_email_templates()
        _create_users()
        _cache_externals()
        _load_courses()
        _set_up_and_run_jobs()
        _set_room_capability()
    return db


def _cache_externals():
    for external in ('calnet', 'canvas', 'kaltura'):
        for path in glob.glob(f"{app.config['FIXTURES_PATH']}/{external}/*.json"):
            with open(path, 'r') as file:
                key = path.split('/')[-1].split('.')[0]
                cache.set(f'{external}/{key}', json.loads(file.read()))


def _load_schemas():
    """Create DB schema from SQL file."""
    with open(app.config['BASE_DIR'] + '/scripts/db/schema.sql', 'r') as ddlfile:
        db.session().execute(text(ddlfile.read()))
        std_commit()


def _load_courses():
    term_id = app.config['CURRENT_TERM_ID']
    db.session.execute(SisSection.__table__.delete().where(SisSection.term_id == term_id))
    save_mock_courses(f"{app.config['FIXTURES_PATH']}/sis/courses.json")
    SisDataRefreshJob.after_sis_data_refresh(term_id=term_id)
    std_commit(allow_test_environment=True)


def _create_blackouts():
    Blackout.create(
        name='An excellent day for an exorcism',
        start_date='12/25/2021',
        end_date='12/25/2021',
    )
    std_commit(allow_test_environment=True)


def _create_email_templates():
    EmailTemplate.create(
        template_type='admin_operator_requested',
        name='Admin alert: operator requested',
        subject_line='Admin alert: operator requested',
        message='Operator requested for class for class <code>course.name</code>',
    )
    EmailTemplate.create(
        template_type='changes_confirmed',
        name='Changes confirmed',
        subject_line='Changes confirmed',
        message='Changes confirmed for class <code>course.name</code>',
    )
    EmailTemplate.create(
        template_type='instructors_added',
        name='Instructor(s) added to class',
        subject_line='Instructor(s) added to class',
        message='Instructor(s) added to class <code>course.name</code>',
    )
    EmailTemplate.create(
        template_type='instructors_removed',
        name='Instructor(s) removed from class',
        subject_line='Instructor(s) removed from class',
        message='Instructor(s) removed from class <code>course.name</code>',
    )
    EmailTemplate.create(
        template_type='multiple_meeting_pattern_change',
        name='Multiple meeting pattern change',
        subject_line='Marvelous multiple meeting patterns',
        message='<code>course.name</code> had a complicated change, better go check it out in Diablo.',
    )
    EmailTemplate.create(
        template_type='new_class_scheduled',
        name='New class scheduled',
        subject_line='New class scheduled: <code>course.name</code>',
        message='Intensely.',
    )
    EmailTemplate.create(
        template_type='no_longer_scheduled',
        name='Class no longer scheduled',
        subject_line='Class no longer scheduled',
        message='Class no longer scheduled: <code>course.name</code>',
    )
    EmailTemplate.create(
        template_type='opted_out',
        name='Opted out',
        subject_line='Opted out',
        message='Class opted out: <code>course.name</code>',
    )
    EmailTemplate.create(
        template_type='remind_scheduled',
        name='Blessed are those who are scheduled',
        subject_line='Did you remember??',
        message='You are scheduled, <code>recipient.name</code>!\n<code>courseList</code>',
    )
    EmailTemplate.create(
        template_type='room_change_no_longer_eligible',
        name='Room change: no longer eligible',
        subject_line='Room change alert',
        message='<code>course.name</code> has changed to a new, ineligible room: <code>course.room</code>',
    )
    EmailTemplate.create(
        template_type='schedule_change',
        name='Schedule change',
        subject_line='Schedule change alert',
        message='<code>course.name</code> has changed to a new room and/or schedule: <code>course.room</code>',
    )
    EmailTemplate.create(
        template_type='semester_start',
        name='Semester start',
        subject_line="It's a new semester, tally ho!",
        message="Well, then let's introduce ourselves. I'm <code>recipient.name</code> and these are my courses:\n<code>courseList</code>",
    )
    std_commit(allow_test_environment=True)


def _create_users():
    for test_user in _test_users:
        user = AdminUser(uid=test_user['uid'])
        db.session.add(user)
        if test_user['deleted_at']:
            AdminUser.delete(user.uid)
    std_commit(allow_test_environment=True)


def _set_up_and_run_jobs():
    Job.create(job_schedule_type='day_at', job_schedule_value='15:00', key='kaltura')
    Job.create(job_schedule_type='minutes', job_schedule_value='60', key='emails')
    Job.create(job_schedule_type='day_at', job_schedule_value='22:00', key='house_keeping')
    Job.create(job_schedule_type='day_at', job_schedule_value='23:00', key='delete_zoom_recordings')
    Job.create(disabled=True, job_schedule_type='minutes', job_schedule_value='120', key='blackouts')
    Job.create(disabled=True, job_schedule_type='minutes', job_schedule_value='120', key='clear_schedules')
    Job.create(disabled=True, job_schedule_type='minutes', job_schedule_value='5', key='doomed_to_fail')
    Job.create(is_schedulable=False, job_schedule_type='day_at', job_schedule_value='16:00', key='remind_instructors')
    Job.create(is_schedulable=False, job_schedule_type='minutes', job_schedule_value='820', key='schedule_updates')
    Job.create(is_schedulable=False, job_schedule_type='minutes', job_schedule_value='720', key='semester_start')
    background_job_manager.start(app)
    HouseKeepingJob(app_context=simply_yield).run()
    std_commit(allow_test_environment=True)


def _set_room_capability():
    for room in Room.all_rooms():
        if room.location in ["O'Brien 212", 'Li Ka Shing 145']:
            Room.set_auditorium(room.id, True)
        if room.location in ['Li Ka Shing 145', 'Barker 101', "O'Brien 212"]:
            Room.update_capability(room.id, 'screencast_and_video')
    std_commit(allow_test_environment=True)


if __name__ == '__main__':
    import diablo.factory
    diablo.factory.create_app()
    load()
