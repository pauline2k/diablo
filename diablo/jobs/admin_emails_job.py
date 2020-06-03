"""
Copyright ©2020. The Regents of the University of California (Regents). All Rights Reserved.

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
from diablo.jobs.base_job import BaseJob
from diablo.jobs.errors import BackgroundJobError
from diablo.lib.interpolator import interpolate_content
from diablo.merged.emailer import get_admin_alert_recipients
from diablo.models.email_template import EmailTemplate
from diablo.models.queued_email import QueuedEmail
from diablo.models.sis_section import SisSection
from flask import current_app as app


class AdminEmailsJob(BaseJob):

    def _run(self):
        self.term_id = app.config['CURRENT_TERM_ID']
        self.courses = SisSection.get_course_changes(term_id=self.term_id)
        self._alert_admin_of_instructor_changes()
        self._alert_admin_of_room_changes()

    @classmethod
    def description(cls):
        names_by_type = EmailTemplate.get_template_type_options()
        template_types = ['admin_alert_instructor_change', 'admin_alert_room_change']
        return f"""
            Queues up admin notifications. Email templates used:
            <ul>
                {''.join(f'<li>{names_by_type.get(template_type)}</li>' for template_type in template_types)}
            </ul>
        """

    @classmethod
    def key(cls):
        return 'admin_emails'

    def _alert_admin_of_instructor_changes(self):
        for course in self.courses:
            if course['scheduled'] and course['scheduled']['hasObsoleteInstructors']:
                self._notify(course=course, template_type='admin_alert_instructor_change')

    def _alert_admin_of_room_changes(self):
        for course in self.courses:
            if course['scheduled'] and course['scheduled']['hasObsoleteRoom']:
                self._notify(course=course, template_type='admin_alert_room_change')

    def _notify(self, course, template_type):
        email_template = EmailTemplate.get_template_by_type(template_type)
        if email_template:
            for recipient in get_admin_alert_recipients():
                message = interpolate_content(
                    templated_string=email_template.message,
                    course=course,
                    recipient_name=recipient['name'],
                )
                subject_line = interpolate_content(
                    templated_string=email_template.subject_line,
                    course=course,
                    recipient_name=recipient['name'],
                )
                QueuedEmail.create(
                    message=message,
                    subject_line=subject_line,
                    recipient=recipient,
                    section_id=course['sectionId'],
                    template_type=template_type,
                    term_id=self.term_id,
                )
        else:
            raise BackgroundJobError(f"""
                No email template of type {template_type} is available.
                Diablo admin NOT notified in regard to course {course['label']}.
            """)
