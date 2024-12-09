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
class TestScheduling0:
    """
    SCENARIO.

    - Section has one instructor, one meeting, and one course site
    - Recordings scheduled via semester start job
    - Instructor selects camera operator and auto-publish, adding course site
    - Series updated
    - Admin reverts to no camera operator and no auto-publish
    - Series updated
    """

    test_data = util.get_test_script_course('test_scheduling_0')
    section = util.get_test_section(test_data)
    admin = User({'uid': util.get_admin_uid()})
    instructor = section.instructors[0]
    meeting = section.meetings[0]
    meeting_schedule = meeting.meeting_schedule
    recording_schedule = RecordingSchedule(section, meeting)
    site = CanvasSite(
        code=f'XENA Scheduling0 - {section.code}',
        name=f'XENA Scheduling0 - {section.code}',
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

    # CREATE COURSE SITE

    def test_create_course_site(self):
        self.canvas_page.create_site(self.section, self.site)
        self.canvas_page.add_user_to_site(self.site, self.instructor, 'Teacher')

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

    # COURSE CAPTURE OPTIONS NOT AVAILABLE PRE-SCHEDULING

    def test_no_collaborator_edits(self):
        self.course_page.load_page(self.section)
        assert not self.course_page.is_present(CoursePage.COLLAB_EDIT_BUTTON)

    def test_no_recording_type_edits(self):
        assert not self.course_page.is_present(CoursePage.RECORDING_TYPE_EDIT_BUTTON)

    def test_no_recording_placement_edits(self):
        assert not self.course_page.is_present(CoursePage.PLACEMENT_EDIT_BUTTON)

    def test_scheduling_upcoming_msg(self):
        assert self.course_page.is_present(CoursePage.SCHEDULING_TO_COME_MSG)
        assert not self.course_page.is_present(CoursePage.SCHEDULED_MSG)
        assert not self.course_page.is_present(CoursePage.UPDATES_QUEUED_MSG)
        assert not self.course_page.is_present(CoursePage.OPT_OUT_QUEUED_MSG)
        assert not self.course_page.is_present(CoursePage.OPT_OUT_DONE_MSG)
        assert not self.course_page.is_present(CoursePage.NOT_ELIGIBLE_MSG)

    # VERIFY COURSE HISTORY

    def test_no_history(self):
        assert not self.course_page.update_history_table_rows()

    # RUN SCHEDULE UPDATE JOB

    def test_schedule_update(self):
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

    def test_series_recordings(self):
        self.room_page.verify_series_recordings(self.recording_schedule)

    def test_verify_printable(self):
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
        assert len(self.kaltura_page.publish_category_els()) == 0
        assert not self.kaltura_page.is_publish_category_present(self.site)

    # VERIFY ANNUNCIATION EMAIL

    def test_receive_annunciation_email(self):
        assert util.get_sent_email_count(EmailTemplateType.INSTR_ANNUNCIATION_NEW_COURSE_SCHED, section=None,
                                         instructor=self.instructor) == 1

    # INSTRUCTOR LOGS IN

    def test_home_page(self):
        self.kaltura_page.close_window_and_switch()
        self.jobs_page.log_out()
        self.course_page.hit_url(self.term.id, self.section.ccn)
        self.login_page.dev_auth(self.instructor.uid)
        self.course_page.wait_for_diablo_title(f'{self.section.code}, {self.section.number}')

    # VERIFY STATIC COURSE SIS DATA

    def test_visible_section_sis_data(self):
        self.course_page.verify_section_sis_data(self.section)

    def test_visible_meeting_sis_data(self):
        self.course_page.verify_meeting_sis_data(self.meeting, idx=0)

    def test_visible_site_ids(self):
        assert self.course_page.visible_course_site_ids() == []

    def test_visible_listings(self):
        listing_codes = [li.code for li in self.section.listings]
        assert self.course_page.visible_cross_listing_codes() == listing_codes

    def test_course_scheduled_msg(self):
        assert self.course_page.is_present(CoursePage.SCHEDULED_MSG)
        assert not self.course_page.is_present(CoursePage.SCHEDULING_TO_COME_MSG)
        assert not self.course_page.is_present(CoursePage.UPDATES_QUEUED_MSG)
        assert not self.course_page.is_present(CoursePage.OPT_OUT_QUEUED_MSG)
        assert not self.course_page.is_present(CoursePage.OPT_OUT_DONE_MSG)
        assert not self.course_page.is_present(CoursePage.NOT_ELIGIBLE_MSG)

    # VERIFY DEFAULT SETTINGS AND EXTERNAL LINKS

    def test_default_instructors(self):
        assert self.course_page.visible_instructor_uids() == [str(self.instructor.uid)]

    def test_no_collaborators(self):
        assert not self.course_page.visible_collaborator_uids()

    def test_default_recording_type(self):
        assert self.course_page.visible_recording_type() == self.recording_schedule.recording_type.value['desc']

    def test_default_recording_placement(self):
        assert self.recording_schedule.recording_placement.value['desc'] in self.course_page.visible_recording_placement()

    def test_no_instructor_kaltura_link(self):
        assert not self.course_page.is_present(self.course_page.kaltura_series_link(self.recording_schedule))

    def test_how_to_publish_from_my_media_link(self):
        title = 'IT - How do I publish media from My Media to a Media Gallery in bCourses?'
        assert self.course_page.external_link_valid(self.course_page.HOW_TO_PUBLISH_LINK, title)

    def test_how_to_embed_in_bcourses_link(self):
        title = 'IT - How do I embed Kaltura media in bCourses using the Rich Content Editor?'
        assert self.course_page.external_link_valid(self.course_page.HOW_TO_EMBED_LINK, title)

    def test_no_how_to_remove_a_recording_link(self):
        assert not self.course_page.is_present(self.course_page.HOW_TO_REMOVE_LINK)

    def test_how_to_download_second_stream_link(self):
        title = 'IT - How do I download the second stream of a dual-stream video?'
        assert self.course_page.external_link_valid(self.course_page.HOW_TO_DOWNLOAD_LINK, title)

    def test_course_capture_faq_link(self):
        title = 'Course Capture FAQ | Research, Teaching, & Learning'
        assert self.course_page.external_link_valid(self.course_page.COURSE_CAPTURE_FAQ_LINK, title)

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

    # SELECT OPTIONS, SAVE

    def test_choose_rec_placement(self):
        self.course_page.cancel_recording_placement_edits()
        self.course_page.click_edit_recording_placement()
        self.course_page.select_recording_placement(RecordingPlacement.PUBLISH_AUTOMATICALLY, sites=[self.site])
        self.course_page.save_recording_placement_edits()
        self.recording_schedule.recording_placement = RecordingPlacement.PUBLISH_AUTOMATICALLY

    def test_choose_rec_type(self):
        self.course_page.click_rec_type_edit_button()
        self.course_page.select_rec_type(RecordingType.VIDEO_WITH_OPERATOR)
        self.course_page.save_recording_type_edits()
        self.recording_schedule.recording_type = RecordingType.VIDEO_WITH_OPERATOR

    def test_rec_type_operator_no_going_back(self):
        assert not self.course_page.is_present(self.course_page.RECORDING_TYPE_EDIT_BUTTON)

    def test_visible_site_ids_updated(self):
        assert self.course_page.visible_course_site_ids() == [self.site.site_id]

    def test_site_link(self):
        assert self.course_page.external_link_valid(CoursePage.selected_placement_site_loc(self.site), self.site.name)

    def test_no_publish_from_my_media_link(self):
        assert not self.course_page.is_present(self.course_page.HOW_TO_PUBLISH_LINK)

    def test_no_how_to_embed_in_bcourses_link(self):
        assert not self.course_page.is_present(self.course_page.HOW_TO_EMBED_LINK)

    def test_how_to_remove_a_recording_link(self):
        title = 'IT - How do I remove media from a bCourses Media Gallery or from My Media?'
        assert self.course_page.external_link_valid(self.course_page.HOW_TO_REMOVE_LINK, title)

    def test_how_to_download_second_stream_link_again(self):
        title = 'IT - How do I download the second stream of a dual-stream video?'
        assert self.course_page.external_link_valid(self.course_page.HOW_TO_DOWNLOAD_LINK, title)

    def test_course_capture_faq_link_again(self):
        title = 'Course Capture FAQ | Research, Teaching, & Learning'
        assert self.course_page.external_link_valid(self.course_page.COURSE_CAPTURE_FAQ_LINK, title)

    def test_no_history_for_instructors(self):
        self.course_page.load_page(self.section)
        assert not self.course_page.update_history_table_rows()

    def test_changes_queued(self):
        assert self.course_page.is_present(CoursePage.UPDATES_QUEUED_MSG)
        assert self.course_page.is_present(CoursePage.SCHEDULED_MSG)

    # VERIFY COURSE HISTORY

    def test_course_history_rec_type(self):
        self.course_page.log_out()
        self.login_page.dev_auth()
        self.ouija_page.click_jobs_link()
        self.course_page.load_page(self.section)
        self.course_page.verify_history_row(field='recording_type',
                                            old_value=RecordingType.VIDEO_SANS_OPERATOR.value['db'],
                                            new_value=RecordingType.VIDEO_WITH_OPERATOR.value['db'],
                                            requestor=self.instructor,
                                            status='queued')

    def test_course_history_rec_placement(self):
        self.course_page.verify_history_row(field='publish_type',
                                            old_value=RecordingPlacement.PLACE_IN_MY_MEDIA.value['db'],
                                            new_value=RecordingPlacement.PUBLISH_AUTOMATICALLY.value['db'],
                                            requestor=self.instructor,
                                            status='queued')

    def test_course_history_canvas_site(self):
        self.course_page.verify_history_row(field='canvas_site_ids',
                                            old_value='—',
                                            new_value=CoursePage.expected_site_ids_converter([self.site]),
                                            requestor=self.instructor,
                                            status='queued')

    # UPDATE SERIES IN KALTURA

    def test_run_kaltura_job(self):
        self.ouija_page.click_jobs_link()
        self.jobs_page.run_settings_update_job_sequence()

    # VERIFY SERIES IN DIABLO

    def test_update_room_series(self):
        self.rooms_page.load_page()
        self.rooms_page.find_room(self.meeting.room)
        self.rooms_page.click_room_link(self.meeting.room)
        self.room_page.wait_for_series_row(self.recording_schedule)

    def test_update_open_printable(self):
        self.room_printable_page.verify_printable(self.recording_schedule)

    # VERIFY SERIES IN KALTURA

    def test_update_series_title_and_desc(self):
        self.room_printable_page.close_printable_schedule()
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

    # VERIFY EMAILS

    def test_update_receive_schedule_conf_email(self):
        assert util.get_sent_email_count(EmailTemplateType.INSTR_CHANGES_CONFIRMED, self.section,
                                         self.instructor) == 1

    def test_update_admin_email_operator_requested(self):
        assert util.get_sent_email_count(EmailTemplateType.ADMIN_OPERATOR_REQUESTED, self.section) == 1

    # REVERT TO MY MEDIA PLACEMENT TYPE AND NO CAMERA OPERATOR

    def test_course_page_revert_placement(self):
        self.kaltura_page.close_window_and_switch()
        self.course_page.load_page(self.section)
        self.course_page.click_edit_recording_placement()
        self.course_page.select_recording_placement(RecordingPlacement.PLACE_IN_MY_MEDIA)
        self.course_page.save_recording_placement_edits()
        self.recording_schedule.recording_placement = RecordingPlacement.PLACE_IN_MY_MEDIA

    def test_course_page_revert_operator(self):
        self.course_page.click_rec_type_edit_button()
        self.course_page.select_rec_type(RecordingType.VIDEO_SANS_OPERATOR)
        self.course_page.save_recording_type_edits()
        self.recording_schedule.recording_type = RecordingType.VIDEO_SANS_OPERATOR

    def test_revert_how_to_publish_from_my_media_link(self):
        self.course_page.log_out()
        self.course_page.hit_url(self.term.id, self.section.ccn)
        self.login_page.dev_auth(self.instructor.uid)
        self.course_page.wait_for_diablo_title(f'{self.section.code}, {self.section.number}')
        title = 'IT - How do I publish media from My Media to a Media Gallery in bCourses?'
        assert self.course_page.external_link_valid(self.course_page.HOW_TO_PUBLISH_LINK, title)

    def test_revert_how_to_embed_in_bcourses_link(self):
        title = 'IT - How do I embed Kaltura media in bCourses using the Rich Content Editor?'
        assert self.course_page.external_link_valid(self.course_page.HOW_TO_EMBED_LINK, title)

    def test_revert_no_how_to_remove_a_recording_link(self):
        assert not self.course_page.is_present(self.course_page.HOW_TO_REMOVE_LINK)

    def test_revert_how_to_download_second_stream_link(self):
        title = 'IT - How do I download the second stream of a dual-stream video?'
        assert self.course_page.external_link_valid(self.course_page.HOW_TO_DOWNLOAD_LINK, title)

    def test_revert_course_capture_faq_link(self):
        title = 'Course Capture FAQ | Research, Teaching, & Learning'
        assert self.course_page.external_link_valid(self.course_page.COURSE_CAPTURE_FAQ_LINK, title)

    def test_update_jobs_revert_placement(self):
        self.course_page.log_out()
        self.login_page.dev_auth()
        self.ouija_page.click_jobs_link()
        self.jobs_page.run_settings_update_job_sequence()

    def test_kaltura_old_series_deleted(self):
        self.kaltura_page.load_event_edit_page(self.recording_schedule.series_id)
        self.kaltura_page.wait_for_title('Access Denied - UC Berkeley - Test')

    def test_kaltura_new_series(self):
        util.get_kaltura_id(self.recording_schedule)
        self.kaltura_page.load_event_edit_page(self.recording_schedule.series_id)
        self.kaltura_page.verify_title_and_desc(self.section, self.meeting)

    def test_kaltura_new_series_collab(self):
        self.kaltura_page.verify_collaborators(self.section)

    def test_kaltura_new_series_schedule(self):
        self.kaltura_page.verify_schedule(self.section, self.meeting)

    def test_kaltura_new_series_publish_status(self):
        self.kaltura_page.verify_publish_status(self.recording_schedule)

    def test_kaltura_new_series_course_site(self):
        assert len(self.kaltura_page.publish_category_els()) == 0
        assert not self.kaltura_page.is_publish_category_present(self.site)

    # VERIFY REVERTED PLACEMENT EMAIL

    def test_reverted_schedule_conf_email(self):
        assert util.get_sent_email_count(EmailTemplateType.INSTR_CHANGES_CONFIRMED, self.section,
                                         self.instructor) == 2

    # VERIFY COURSE HISTORY

    def test_course_history_rec_type_updated(self):
        self.course_page.load_page(self.section)
        self.course_page.verify_history_row(field='recording_type',
                                            old_value=RecordingType.VIDEO_SANS_OPERATOR.value['db'],
                                            new_value=RecordingType.VIDEO_WITH_OPERATOR.value['db'],
                                            requestor=self.instructor,
                                            status='succeeded',
                                            published=True)

    def test_course_history_rec_placement_updated(self):
        self.course_page.verify_history_row(field='publish_type',
                                            old_value=RecordingPlacement.PLACE_IN_MY_MEDIA.value['db'],
                                            new_value=RecordingPlacement.PUBLISH_AUTOMATICALLY.value['db'],
                                            requestor=self.instructor,
                                            status='succeeded',
                                            published=True)

    def test_course_history_canvas_site_updated(self):
        self.course_page.verify_history_row(field='canvas_site_ids',
                                            old_value='—',
                                            new_value=CoursePage.expected_site_ids_converter([self.site]),
                                            requestor=self.instructor,
                                            status='succeeded',
                                            published=True)

    def test_course_history_rec_placement_reverted(self):
        self.course_page.verify_history_row(field='publish_type',
                                            old_value=RecordingPlacement.PUBLISH_AUTOMATICALLY.value['db'],
                                            new_value=RecordingPlacement.PLACE_IN_MY_MEDIA.value['db'],
                                            requestor=self.admin,
                                            status='succeeded',
                                            published=True)

    def test_course_history_rec_type_reverted(self):
        self.course_page.verify_history_row(field='recording_type',
                                            old_value=RecordingType.VIDEO_WITH_OPERATOR.value['db'],
                                            new_value=RecordingType.VIDEO_SANS_OPERATOR.value['db'],
                                            requestor=self.admin,
                                            status='succeeded',
                                            published=True)
