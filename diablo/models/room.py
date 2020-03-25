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

from datetime import datetime

from diablo import db, std_commit
from diablo.lib.util import to_isoformat
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import ENUM


room_capability_type = ENUM(
    'screencast',
    'screencast_and_video',
    name='room_capability_types',
    create_type=False,
)


class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, nullable=False, primary_key=True)  # noqa: A003
    location = db.Column(db.String(255), nullable=False, unique=True)
    capability = db.Column(room_capability_type)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __init__(
            self,
            location,
            capability,
    ):
        self.location = location
        self.capability = capability

    def __repr__(self):
        return f"""<Room
                    id={self.id},
                    location={self.location},
                    capability={self.capability},
                    created_at={self.created_at}>
                """

    @classmethod
    def create(cls, location, capability=None):
        room = cls(location=location, capability=capability)
        db.session.add(room)
        std_commit()
        return room

    @classmethod
    def find_room(cls, location):
        return cls.query.filter_by(location=location).first()

    @classmethod
    def get_room(cls, room_id):
        return cls.query.filter_by(id=room_id).first()

    @classmethod
    def all_rooms(cls):
        return cls.query.order_by(cls.capability, cls.location).all()

    @classmethod
    def total_room_count(cls):
        return db.session.query(func.count(cls.id)).scalar()

    @classmethod
    def get_all_locations(cls):
        result = db.session.execute(text('SELECT location FROM rooms'))
        return [row['location'] for row in result]

    @classmethod
    def update_capability(cls, room_id, capability):
        room = cls.query.filter_by(id=room_id).first()
        room.capability = capability
        db.session.add(room)
        std_commit()
        return room

    @classmethod
    def get_room_capability_options(cls):
        return {
            'screencast': 'Screencast',
            'screencast_and_video': 'Screencast + Video',
        }

    def to_api_json(self):
        all_options = self.get_room_capability_options()
        if self.capability:
            capability_name = all_options[self.capability]
            capture_options = all_options
            if self.capability == 'screencast':
                capture_options.pop('screencast_and_video')
        else:
            capability_name = None
            capture_options = None
        return {
            'id': self.id,
            'location': self.location,
            'capability': self.capability,
            'capabilityName': capability_name,
            'captureOptions': capture_options,
            'createdAt': to_isoformat(self.created_at),
        }
