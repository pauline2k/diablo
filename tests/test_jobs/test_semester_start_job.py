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
from diablo import std_commit
from diablo.jobs.semester_start_job import SemesterStartJob
from diablo.jobs.tasks.queued_emails_task import QueuedEmailsTask
from diablo.models.queued_email import QueuedEmail
from diablo.models.scheduled import Scheduled
from diablo.models.sent_email import SentEmail
from flask import current_app as app
from tests.util import simply_yield, test_approvals_workflow


class TestSemesterStartJob:

    def test_semester_start(self):
        """Eligible courses are scheduled for recording by default at semester start."""
        with test_approvals_workflow(app):
            term_id = app.config['CURRENT_TERM_ID']
            instructor_uid = '10008'
            section_ids = ['50007', '50010']

            # Verify that nothing is scheduled
            assert Scheduled.get_all_scheduled(term_id=term_id) == []

            emails_to_instructor_count = len(SentEmail.get_emails_sent_to(instructor_uid))
            SemesterStartJob(simply_yield).run()
            std_commit(allow_test_environment=True)
            for section_id in section_ids:
                scheduled = Scheduled.get_scheduled(section_id=section_id, term_id=term_id)
                assert instructor_uid in scheduled.instructor_uids

            # Verify one email sent to each instructor, even in the case of multiple eligible courses.
            emails_queued_for_instructor = [e for e in QueuedEmail.get_all(term_id=term_id) if e.recipient['uid'] == instructor_uid]
            assert len(emails_queued_for_instructor) == 1
            assert emails_queued_for_instructor[0].template_type == 'semester_start'
            assert emails_queued_for_instructor[0].message == "Well, then let's introduce ourselves. "\
                "I'm William Kinderman and these are my courses:\n"\
                'IND ENG 95: Richard Newton Lecture Series\n'\
                'MATH C51: Linear algebra and differential calculus'

            QueuedEmailsTask().run()
            emails_sent = SentEmail.get_emails_sent_to(instructor_uid)
            assert len(emails_sent) == emails_to_instructor_count + 1
            email_sent = emails_sent[-1]
            assert email_sent.template_type == 'semester_start'
            assert email_sent.term_id == term_id

            """If recordings were already scheduled, send no additional email."""
            emails_to_instructor_count = len(SentEmail.get_emails_sent_to(instructor_uid))
            SemesterStartJob(simply_yield).run()
            assert len(SentEmail.get_emails_sent_to(instructor_uid)) == emails_to_instructor_count