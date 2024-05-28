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

from flask import current_app as app
import pytest
from xena.models.canvas_site import CanvasSite
from xena.models.email_template_type import EmailTemplateType
from xena.models.publish_type import PublishType
from xena.models.recording_schedule import RecordingSchedule
from xena.models.recording_scheduling_status import RecordingSchedulingStatus
from xena.models.recording_type import RecordingType
from xena.pages.course_page import CoursePage
from xena.test_utils import util


@pytest.mark.usefixtures('page_objects')
class TestScheduling1:

    test_data = util.get_test_script_course('test_scheduling_1')
    section = util.get_test_section(test_data)
    meeting = section.meetings[0]
    recording_schedule = RecordingSchedule(section)
    site = CanvasSite(
        code=f'XENA Scheduling1 - {section.code}',
        name=f'XENA Scheduling1 - {section.code}',
        site_id=None,
    )

    # DELETE PRE-EXISTING DATA

    def test_disable_jobs(self):
        self.login_page.load_page()
        self.login_page.dev_auth()
        self.ouija_page.click_jobs_link()
        self.jobs_page.run_emails_job()
        self.jobs_page.disable_all_jobs()

    def test_create_blackouts(self):
        self.jobs_page.click_blackouts_link()
        self.blackouts_page.delete_all_blackouts()
        self.blackouts_page.create_all_blackouts()

    def test_delete_old_diablo_and_kaltura(self):
        self.kaltura_page.log_in_via_calnet(self.calnet_page)
        self.kaltura_page.reset_test_data(self.term, self.recording_schedule)
        util.reset_section_test_data(self.section)
        self.recording_schedule.scheduling_status = RecordingSchedulingStatus.NOT_SCHEDULED

    # TODO - delete old course sites?

    def test_delete_old_email(self):
        util.reset_sent_email_test_data(self.section)

    # CHECK FILTERS - NOT SCHEDULED

    def test_not_scheduled_filter_all(self):
        self.ouija_page.load_page()
        self.ouija_page.search_for_course_code(self.section)
        self.ouija_page.filter_for_all()
        assert self.ouija_page.is_course_in_results(self.section)

    def test_not_scheduled_sched_status(self):
        visible_status = self.ouija_page.course_row_sched_status_el(self.section).text.strip()
        assert visible_status == self.recording_schedule.scheduling_status.value

    def test_not_scheduled_filter_opted_out(self):
        self.ouija_page.filter_for_opted_out()
        assert not self.ouija_page.is_course_in_results(self.section)

    def test_not_scheduled_filter_scheduled(self):
        self.ouija_page.filter_for_scheduled()
        assert not self.ouija_page.is_course_in_results(self.section)

    def test_not_scheduled_filter_no_instructors(self):
        self.ouija_page.filter_for_no_instructors()
        assert not self.ouija_page.is_course_in_results(self.section)

    # RUN SEMESTER START JOB

    def test_semester_start(self):
        self.jobs_page.load_page()
        self.jobs_page.run_semester_start_job()
        assert util.get_kaltura_id(self.recording_schedule, self.term)
        self.recording_schedule.recording_type = RecordingType.VIDEO_SANS_OPERATOR
        self.recording_schedule.publish_type = PublishType.PUBLISH_TO_MY_MEDIA
        self.recording_schedule.scheduling_status = RecordingSchedulingStatus.SCHEDULED

    def test_kaltura_blackouts(self):
        self.jobs_page.run_blackouts_job()

    # CHECK FILTERS - SCHEDULED

    def test_scheduled_filter_all(self):
        self.ouija_page.load_page()
        self.ouija_page.search_for_course_code(self.section)
        self.ouija_page.filter_for_all()
        assert self.ouija_page.is_course_in_results(self.section)

    def test_scheduled_sched_status(self):
        visible_status = self.ouija_page.course_row_sched_status_el(self.section).text.strip()
        assert visible_status == self.recording_schedule.scheduling_status.value

    def test_scheduled_filter_opted_out(self):
        self.ouija_page.filter_for_opted_out()
        assert not self.ouija_page.is_course_in_results(self.section)

    def test_scheduled_filter_scheduled(self):
        self.ouija_page.filter_for_scheduled()
        assert self.ouija_page.is_course_in_results(self.section)

    def test_scheduled_filter_no_instructors(self):
        self.ouija_page.filter_for_no_instructors()
        assert not self.ouija_page.is_course_in_results(self.section)

    # VERIFY SERIES IN DIABLO

    def test_room_series(self):
        self.rooms_page.load_page()
        self.rooms_page.find_room(self.meeting.room)
        self.rooms_page.click_room_link(self.meeting.room)
        self.room_page.wait_for_series_row(self.recording_schedule)

    def test_room_series_link(self):
        expected = f'{self.section.code}, {self.section.number} ({self.term.name})'
        assert self.room_page.series_row_kaltura_link_text(self.recording_schedule) == expected

    def test_room_series_schedule(self):
        self.room_page.verify_series_schedule(self.section, self.meeting, self.recording_schedule)

    def test_room_series_recordings(self):
        self.room_page.verify_series_recordings(self.section, self.meeting, self.recording_schedule)

    def test_room_series_blackouts(self):
        self.room_page.verify_series_blackouts(self.section, self.meeting, self.recording_schedule)

    def test_printable(self):
        self.room_printable_page.verify_printable(self.section, self.meeting, self.recording_schedule)

    # VERIFY SERIES IN KALTURA

    def test_click_series_link(self):
        self.room_printable_page.close_printable_schedule()
        self.course_page.load_page(self.section)
        self.course_page.click_kaltura_series_link(self.recording_schedule)
        self.kaltura_page.wait_for_delete_button()

    def test_series_title_and_desc(self):
        self.kaltura_page.verify_title_and_desc(self.section, self.meeting)

    def test_series_collab(self):
        self.kaltura_page.verify_collaborators(self.section)

    def test_series_schedule(self):
        self.kaltura_page.verify_schedule(self.section, self.meeting)

    def test_series_publish_status(self):
        assert self.kaltura_page.is_private()

    def test_kaltura_course_site(self):
        assert len(self.kaltura_page.publish_category_els()) == 0

    # VERIFY ANNUNCIATION EMAIL

    def test_receive_annunciation_email(self):
        self.kaltura_page.close_window_and_switch()
        assert util.get_sent_email_count(EmailTemplateType.INSTR_ANNUNCIATION_SEM_START, self.section,
                                         self.section.instructors[0]) == 1

    # VERIFY STATIC COURSE SIS DATA

    def test_visible_ccn(self):
        self.course_page.load_page(self.section)
        assert self.course_page.visible_ccn() == self.section.ccn

    def test_visible_course_title(self):
        assert self.course_page.visible_course_title() == self.section.title

    def test_visible_instructors(self):
        instructor_names = [f'{i.first_name} {i.last_name}'.strip() for i in self.section.instructors]
        assert self.course_page.visible_instructors() == instructor_names

    def test_visible_meeting_days(self):
        term_dates = f'{CoursePage.expected_term_date_str(self.meeting.start_date, self.meeting.end_date)}'
        assert term_dates in self.course_page.visible_meeting_days()[0]

    def test_visible_meeting_time(self):
        assert self.course_page.visible_meeting_time()[0] == f'{self.meeting.start_time} - {self.meeting.end_time}'

    def test_visible_room(self):
        assert self.course_page.visible_rooms()[0] == self.meeting.room.name

    def test_visible_site_ids(self):
        assert self.course_page.visible_course_site_ids() == []

    def test_visible_listings(self):
        listing_codes = [li.code for li in self.section.listings]
        assert self.course_page.visible_cross_listing_codes() == listing_codes

    # VERIFY AVAILABLE OPTIONS

    def test_rec_type_options(self):
        self.course_page.click_rec_type_input()
        visible_opts = self.course_page.visible_menu_options()
        expected = [
            RecordingType.VIDEO_WITH_OPERATOR.value['option'],
            RecordingType.VIDEO_SANS_OPERATOR.value['option'],
        ]
        assert visible_opts == expected

    def test_publish_options(self):
        self.course_page.hit_escape()
        self.course_page.click_publish_type_input()
        visible_opts = self.course_page.visible_menu_options()
        assert visible_opts == [
            PublishType.PUBLISH_AUTOMATICALLY.value,
            PublishType.PUBLISH_TO_PENDING.value,
            PublishType.PUBLISH_TO_MY_MEDIA.value,
        ]

    # SELECT OPTIONS, SAVE

    def test_choose_publish_type(self):
        self.course_page.select_publish_type(PublishType.PUBLISH_AUTOMATICALLY.value)
        self.recording_schedule.publish_type = PublishType.PUBLISH_AUTOMATICALLY

    # TODO - verify no course sites available to add

    def test_approve(self):
        self.course_page.click_approve_button()

    # TODO - revise this
    def test_confirmation(self):
        msg = 'This course is currently queued for scheduling. Recordings will be scheduled in an hour or less. Approved by you.'
        self.course_page.wait_for_approvals_msg(msg)

    # VERIFY COURSE HISTORY

    # TODO def test_course_history_updates_pending(self):

    # TODO - what does ouija page row display while updates are pending?
    # TODO - what does room page row display while updates are pending?
    # TODO - what does course page display while updates are pending?

    # UPDATE SERIES IN KALTURA

    def test_run_kaltura_job(self):
        self.ouija_page.click_jobs_link()
        self.jobs_page.run_kaltura_job()
        self.jobs_page.run_emails_job()

    # VERIFY SERIES IN KALTURA

    def test_update_click_series_link(self):
        self.course_page.load_page(self.section)
        self.course_page.click_kaltura_series_link(self.recording_schedule)
        self.kaltura_page.wait_for_delete_button()

    def test_update_series_title_and_desc(self):
        self.kaltura_page.verify_title_and_desc(self.section, self.meeting)

    def test_update_series_collab(self):
        self.kaltura_page.verify_collaborators(self.section)

    def test_update_schedule(self):
        self.kaltura_page.verify_schedule(self.section, self.meeting)

    # TODO - what does publish-automatically look like?

    def test_update_series_publish_status(self):
        self.kaltura_page.reload_page()
        self.kaltura_page.wait_for_publish_category_el()
        assert self.kaltura_page.is_published()

    def test_update_kaltura_course_site(self):
        assert len(self.kaltura_page.publish_category_els()) == 0

    # VERIFY EMAIL

    def test_update_receive_schedule_conf_email(self):
        self.kaltura_page.close_window_and_switch()
        assert util.get_sent_email_count(EmailTemplateType.INSTR_CHANGES_CONFIRMED, self.section,
                                         self.section.instructors[0]) == 1

    # VERIFY COURSE HISTORY

    # TODO def test_course_history_updates_done(self):

    # CREATE COURSE SITE

    def test_create_course_site(self):
        self.canvas_page.provision_site(self.section, [self.section.ccn], self.site)

    def test_enable_media_gallery(self):
        if self.canvas_page.is_tool_configured(app.config['CANVAS_MEDIA_GALLERY_TOOL']):
            self.canvas_page.load_site(self.site.site_id)
            self.canvas_page.enable_media_gallery(self.site)
            self.canvas_page.click_media_gallery_tool()
        else:
            app.logger.info('Media Gallery is not properly configured')
            raise

    def test_enable_my_media(self):
        if self.canvas_page.is_tool_configured(app.config['CANVAS_MY_MEDIA_TOOL']):
            self.canvas_page.load_site(self.site.site_id)
            self.canvas_page.enable_my_media(self.site)
            self.canvas_page.click_my_media_tool()
        else:
            app.logger.info('My Media is not properly configured')
            raise

    def test_add_new_site(self):
        self.course_page.load_page(self.section)

    # TODO - verify site options include newly created site

    # TODO - add site to publication channels

    def test_site_link(self):
        assert self.course_page.external_link_valid(CoursePage.course_site_link_locator(self.site), self.site.name)

    def test_new_site_run_kaltura_job(self):
        self.ouija_page.click_jobs_link()
        # TODO - run updates job
        self.jobs_page.run_kaltura_job()
        self.jobs_page.run_emails_job()

    # VERIFY SERIES IN KALTURA

    def test_canvas_site_click_series_link(self):
        self.course_page.load_page(self.section)
        self.course_page.click_kaltura_series_link(self.recording_schedule)
        self.kaltura_page.wait_for_delete_button()

    def test_canvas_site_series_title_and_desc(self):
        self.kaltura_page.verify_title_and_desc(self.section, self.meeting)

    def test_canvas_site_series_collab(self):
        self.kaltura_page.verify_collaborators(self.section)

    def test_canvas_site_schedule(self):
        self.kaltura_page.verify_schedule(self.section, self.meeting)

    # TODO - what does publish-automatically look like?

    def test_canvas_site_series_publish_status(self):
        self.kaltura_page.reload_page()
        self.kaltura_page.wait_for_publish_category_el()
        assert self.kaltura_page.is_published()

    def test_canvas_site_kaltura_course_site(self):
        assert len(self.kaltura_page.publish_category_els()) == 2
        assert self.kaltura_page.is_publish_category_present(self.site)

    # VERIFY COURSE HISTORY

    # TODO def test_course_history_new_site(self):

    # VERIFY REMINDER EMAIL

    # TODO