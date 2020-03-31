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

from diablo.api.errors import BadRequestError, ResourceNotFoundError
from diablo.api.util import admin_required
from diablo.externals.email import get_email_template_codes, send_test_email
from diablo.lib.http import tolerant_jsonify
from diablo.merged.sis import get_section
from diablo.models.email_template import EmailTemplate
from flask import current_app as app, request
from flask_login import current_user


@app.route('/api/email_templates/all')
@admin_required
def get_all_email_templates():
    return tolerant_jsonify([template.to_api_json() for template in EmailTemplate.all_templates()])


@app.route('/api/email_templates/names')
@admin_required
def get_email_templates_names():
    return tolerant_jsonify(EmailTemplate.get_all_templates_names())


@app.route('/api/email_template/<template_id>')
@admin_required
def get_email_template(template_id):
    email_template = EmailTemplate.get_template(template_id)
    if email_template:
        return tolerant_jsonify(email_template.to_api_json())
    else:
        raise ResourceNotFoundError('No such email_template')


@app.route('/api/email_template/codes')
@admin_required
def get_template_codes():
    return tolerant_jsonify(get_email_template_codes())


@app.route('/api/email_template/create', methods=['POST'])
@admin_required
def create():
    params = request.get_json()
    template_type = params.get('templateType')
    name = params.get('name')
    subject_line = params.get('subjectLine')
    message = params.get('message')

    if None in [template_type, name, subject_line, message]:
        raise BadRequestError('Required parameters are missing.')

    email_template = EmailTemplate.create(
        template_type=template_type,
        name=name,
        subject_line=subject_line,
        message=message,
    )
    return tolerant_jsonify(email_template.to_api_json())


@app.route('/api/email_template/test/<template_id>')
@admin_required
def test_email_template(template_id):
    email_template = EmailTemplate.get_template(template_id)
    if email_template:
        course = get_section(term_id=app.config['CURRENT_TERM_ID'], section_id='12597')
        send_test_email(
            email_template=EmailTemplate.get_template(template_id),
            recipient=current_user,
            course=course,
        )
        return tolerant_jsonify({'message': f'Email sent to {current_user.email}'}), 200
    else:
        raise ResourceNotFoundError('No such email_template')


@app.route('/api/email_template/update', methods=['POST'])
@admin_required
def update():
    params = request.get_json()
    template_id = params.get('templateId')
    email_template = EmailTemplate.get_template(template_id) if template_id else None
    if email_template:
        template_type = params.get('templateType')
        name = params.get('name')
        subject_line = params.get('subjectLine')
        message = params.get('message')

        if None in [template_type, name, subject_line, message]:
            raise BadRequestError('Required parameters are missing.')

        email_template = EmailTemplate.update(
            template_id=template_id,
            template_type=template_type,
            name=name,
            subject_line=subject_line,
            message=message,
        )
        return tolerant_jsonify(email_template.to_api_json())
    else:
        raise ResourceNotFoundError('No such email template')