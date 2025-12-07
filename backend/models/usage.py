from backend.models.user import db
from datetime import datetime
import hashlib


class UsageTracking(db.Model):
    """Track anonymous user submissions by IP + fingerprint"""
    __tablename__ = 'usage_tracking'

    id = db.Column(db.Integer, primary_key=True)
    identifier_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    submission_count = db.Column(db.Integer, default=0)
    last_submission = db.Column(db.DateTime, default=datetime.utcnow)
    year = db.Column(db.Integer, default=lambda: datetime.utcnow().year)

    @staticmethod
    def generate_identifier(ip_address, fingerprint):
        """Generate a hashed identifier from IP and browser fingerprint"""
        combined = f"{ip_address}:{fingerprint}"
        return hashlib.sha256(combined.encode()).hexdigest()

    @classmethod
    def get_or_create(cls, ip_address, fingerprint):
        """Get existing tracking record or create new one"""
        identifier = cls.generate_identifier(ip_address, fingerprint)
        current_year = datetime.utcnow().year

        record = cls.query.filter_by(identifier_hash=identifier).first()

        if record:
            # Reset counter if it's a new year
            if record.year != current_year:
                record.submission_count = 0
                record.year = current_year
                db.session.commit()
        else:
            record = cls(
                identifier_hash=identifier,
                submission_count=0,
                year=current_year
            )
            db.session.add(record)
            db.session.commit()

        return record

    def increment_submission(self):
        """Increment submission count"""
        self.submission_count += 1
        self.last_submission = datetime.utcnow()
        db.session.commit()

    def can_submit(self, max_submissions):
        """Check if user can make another submission"""
        return self.submission_count < max_submissions
