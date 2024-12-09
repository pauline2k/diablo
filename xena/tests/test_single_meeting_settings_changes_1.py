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

import pytest
from xena.models.canvas_site import CanvasSite
from xena.models.email_template_type import EmailTemplateType
from xena.models.recording_placement import RecordingPlacement
from xena.models.recording_schedule import RecordingSchedule
from xena.models.recording_type import RecordingType
from xena.models.user import User
from xena.pages.course_page import CoursePage
from xena.test_utils import util


@pytest.mark.usefixtures('page_objects')
class TestScheduling1:
    """
    SCENARIO.

    - Section has one instructor and one meeting
    - Recordings scheduled via scheduling update job
    - Course site created, admin selects auto-publish and enters course site ID
    - Series updated
    """

    test_data = util.get_test_script_course('test_scheduling_1')
    admin = User({'uid': util.get_admin_uid()})
    section = util.get_test_section(test_data)
    instructor = section.instructors[0]
    meeting = section.meetings[0]
    meeting_schedule = meeting.meeting_schedule
    recording_schedule = RecordingSchedule(section, meeting)
    site = CanvasSite(
        code=f'XENA Scheduling1 - {section.code}',
        name=f'XENA Scheduling1 - {section.code}',
        site_id=None,
    )

    # DELETE PRE-EXISTING DATA

    def test_setup(self):
        self.login_page.load_page()
        self.login_page.dev_auth()

        self.ouija_page.click_jobs_link()
        self.jobs_page.disable_all_jobs()

        self.jobs_page.click_blackouts_link()
        self.blackouts_page.create_all_blackouts()

        self.kaltura_page.log_in_via_calnet(self.calnet_page)
        self.kaltura_page.reset_test_data(self.section)

        util.reset_section_test_data(self.section)

        util.reset_sent_email_test_data(self.section)
        util.reset_sent_email_test_data(section=None, instructor=self.instructor)

    # CHECK FILTERS - NOT SCHEDULED

    def test_not_scheduled_filter_all(self):
        self.ouija_page.load_page()
        self.ouija_page.search_for_course_code(self.section)
        self.ouija_page.filter_for_all()
        assert self.ouija_page.is_course_in_results(self.section)

    def test_not_scheduled_sched_status(self):
        assert self.ouija_page.visible_course_row_sched_status(self.section) == 'Not Scheduled'

    def test_not_scheduled_filter_opted_out(self):
        self.ouija_page.filter_for_opted_out()
        assert not self.ouija_page.is_course_in_results(self.section)

    def test_not_scheduled_filter_scheduled(self):
        self.ouija_page.filter_for_scheduled()
        assert not self.ouija_page.is_course_in_results(self.section)

    def test_not_scheduled_filter_no_instructors(self):
        self.ouija_page.filter_for_no_instructors()
        assert not self.ouija_page.is_course_in_results(self.section)

    # SCHEDULE RECORDINGS

    def test_semester_start(self):
        self.jobs_page.load_page()
        self.jobs_page.run_schedule_update_job_sequence()
        assert util.get_kaltura_id(self.recording_schedule)
        self.recording_schedule.recording_type = RecordingType.VIDEO_SANS_OPERATOR
        self.recording_schedule.recording_placement = RecordingPlacement.PLACE_IN_MY_MEDIA

    # CHECK FILTERS - SCHEDULED

    def test_scheduled_filter_all(self):
        self.ouija_page.load_page()
        self.ouija_page.search_for_course_code(self.section)
        self.ouija_page.filter_for_all()
        assert self.ouija_page.is_course_in_results(self.section)

    def test_scheduled_sched_status(self):
        assert self.ouija_page.visible_course_row_sched_status(self.section) == 'Scheduled'

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
        self.room_page.verify_series_link_text(self.recording_schedule)

    def test_room_series_schedule(self):
        self.room_page.verify_series_schedule(self.recording_schedule)

    def test_room_series_recordings(self):
        self.room_page.verify_series_recordings(self.recording_schedule)

    def test_printable(self):
        self.room_printable_page.verify_printable(self.recording_schedule)

    # VERIFY SERIES IN KALTURA

    def test_series_title_and_desc(self):
        self.room_printable_page.close_printable_schedule()
        self.course_page.load_page(self.section)
        self.course_page.click_kaltura_series_link(self.recording_schedule)
        self.kaltura_page.verify_title_and_desc(self.section, self.meeting)

    def test_series_collab(self):
        self.kaltura_page.verify_collaborators(self.section)

    def test_series_schedule(self):
        self.kaltura_page.verify_schedule(self.section, self.meeting)

    def test_series_publish_status(self):
        self.kaltura_page.verify_publish_status(self.recording_schedule)

    def test_kaltura_course_site(self):
        self.kaltura_page.verify_site_categories([])

    # VERIFY ANNUNCIATION EMAIL

    def test_receive_annunciation_email(self):
        assert util.get_sent_email_count(EmailTemplateType.INSTR_ANNUNCIATION_NEW_COURSE_SCHED, section=None,
                                         instructor=self.instructor) == 1

    # VERIFY STATIC COURSE SIS DATA

    def test_visible_section_sis_data(self):
        self.kaltura_page.close_window_and_switch()
        self.course_page.load_page(self.section)
        self.course_page.verify_section_sis_data(self.section)

    def test_visible_meeting_sis_data(self):
        self.course_page.verify_meeting_sis_data(self.meeting, idx=0)

    def test_visible_site_ids(self):
        assert self.course_page.visible_course_site_ids() == []

    def test_visible_listings(self):
        listing_codes = [li.code for li in self.section.listings]
        assert self.course_page.visible_cross_listing_codes() == listing_codes

    # VERIFY AVAILABLE OPTIONS

    def test_rec_type_options(self):
        self.course_page.click_rec_type_edit_button()
        assert self.course_page.is_present(self.course_page.RECORDING_TYPE_NO_OP_RADIO)
        assert self.course_page.is_present(self.course_page.RECORDING_TYPE_OP_RADIO)

    def test_rec_placement_options(self):
        self.course_page.cancel_recording_type_edits()
        self.course_page.click_edit_recording_placement()
        assert self.course_page.is_present(self.course_page.PLACEMENT_MY_MEDIA_RADIO)
        assert self.course_page.is_present(self.course_page.PLACEMENT_AUTOMATIC_RADIO)

    def test_no_changes_to_rec_placement(self):
        self.course_page.select_recording_placement(RecordingPlacement.PUBLISH_AUTOMATICALLY)
        assert not self.course_page.element(self.course_page.PLACEMENT_SAVE_BUTTON).is_enabled()

    # CREATE COURSE SITE

    def test_create_course_site(self):
        self.canvas_page.create_site(self.section, self.site)
        self.canvas_page.add_user_to_site(self.site, self.instructor, 'TA')

    def test_add_new_site(self):
        self.course_page.load_page(self.section)
        self.course_page.click_edit_recording_placement()
        self.course_page.enter_recording_placement(RecordingPlacement.PUBLISH_AUTOMATICALLY, sites=[self.site])
        self.course_page.save_recording_placement_edits()
        self.recording_schedule.recording_placement = RecordingPlacement.PUBLISH_AUTOMATICALLY

    def test_visible_site_ids_updated(self):
        assert self.course_page.visible_course_site_ids() == [self.site.site_id]

    # VERIFY COURSE HISTORY

    def test_course_history_rec_type(self):
        self.course_page.load_page(self.section)
        self.course_page.verify_history_row(field='publish_type',
                                            old_value=RecordingPlacement.PLACE_IN_MY_MEDIA.value['db'],
                                            new_value=RecordingPlacement.PUBLISH_AUTOMATICALLY.value['db'],
                                            requestor=self.admin,
                                            status='queued')

    def test_course_history_canvas_site(self):
        self.course_page.verify_history_row(field='canvas_site_ids',
                                            old_value='—',
                                            new_value=CoursePage.expected_site_ids_converter([self.site]),
                                            requestor=self.admin,
                                            status='queued')

    def test_changes_queued(self):
        assert self.course_page.is_present(CoursePage.UPDATES_QUEUED_MSG)
        assert self.course_page.is_present(CoursePage.SCHEDULED_MSG)

    # UPDATE SERIES IN KALTURA

    def test_run_kaltura_job(self):
        self.ouija_page.click_jobs_link()
        self.jobs_page.run_settings_update_job_sequence()

    # VERIFY SERIES IN KALTURA

    def test_update_series_title_and_desc(self):
        self.course_page.load_page(self.section)
        self.course_page.click_kaltura_series_link(self.recording_schedule)
        self.kaltura_page.verify_title_and_desc(self.section, self.meeting)

    def test_update_series_collab(self):
        self.kaltura_page.verify_collaborators(self.section)

    def test_update_schedule(self):
        self.kaltura_page.verify_schedule(self.section, self.meeting)

    def test_update_series_publish_status(self):
        self.kaltura_page.reload_page()
        self.kaltura_page.wait_for_publish_category_el()
        self.kaltura_page.verify_publish_status(self.recording_schedule)

    def test_update_kaltura_course_site(self):
        self.kaltura_page.verify_site_categories([self.site])

    # VERIFY EMAIL

    def test_update_receive_schedule_conf_email(self):
        assert util.get_sent_email_count(EmailTemplateType.INSTR_CHANGES_CONFIRMED, self.section,
                                         self.instructor) == 1

    # VERIFY COURSE HISTORY

    def test_course_history_rec_type_updated(self):
        self.kaltura_page.close_window_and_switch()
        self.course_page.load_page(self.section)
        self.course_page.verify_history_row(field='publish_type',
                                            old_value=RecordingPlacement.PLACE_IN_MY_MEDIA.value['db'],
                                            new_value=RecordingPlacement.PUBLISH_AUTOMATICALLY.value['db'],
                                            requestor=self.admin,
                                            status='succeeded',
                                            published=True)

    def test_course_history_canvas_site_updated(self):
        self.course_page.verify_history_row(field='canvas_site_ids',
                                            old_value='—',
                                            new_value=CoursePage.expected_site_ids_converter([self.site]),
                                            requestor=self.admin,
                                            status='succeeded',
                                            published=True)

    def test_changes_no_longer_queued(self):
        assert not self.course_page.is_present(CoursePage.UPDATES_QUEUED_MSG)
