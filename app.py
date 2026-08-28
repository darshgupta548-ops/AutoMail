"""Flask application and minimal API for AUTO-MAIL email jobs."""

from datetime import date, time
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from extensions import db
from models.email_context import EmailContext
from models.email_job import EmailJob, JobStatus
from services import asset_service, email_maker, sense_maker


def _parse_date(value):
    if not isinstance(value, str):
        raise ValueError("event_date must be a valid ISO date (YYYY-MM-DD).")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("event_date must be a valid ISO date (YYYY-MM-DD).") from error


def _parse_time(value, field_name):
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a valid time.")
    try:
        return time.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be a valid time.") from error


def _required_text(payload, field_name):
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
    return value.strip()


def _validate_job_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    status = payload.get("status", JobStatus.DRAFT)
    if status not in JobStatus.ALL:
        raise ValueError("status must be one of the defined workflow states.")

    end_time = payload.get("event_end_time")
    end_time = None if end_time in (None, "") else _parse_time(end_time, "event_end_time")

    return {
        "event_name": _required_text(payload, "event_name"),
        "event_date": _parse_date(payload.get("event_date")),
        "event_start_time": _parse_time(payload.get("event_start_time"), "event_start_time"),
        "event_end_time": end_time,
        "event_venue": payload.get("event_venue"),
        "registration_url": payload.get("registration_url"),
        "event_description": _required_text(payload, "event_description"),
        "event_whatsapp_message": payload.get("event_whatsapp_message"),
        "email_context": payload.get("email_context"),
        "event_poster": payload.get("event_poster"),
        "email_bg": payload.get("email_bg"),
        "event_palette": payload.get("event_palette"),
        "event_typography": payload.get("event_typography"),
        "email_html": payload.get("email_html"),
        "status": status,
    }


def create_app(test_config=None):
    """Build the Flask app and configure the SQLite database."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{Path(app.instance_path) / 'automail.db'}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    with app.app_context():
        db.create_all()

    @app.get("/")
    @app.get("/jobs/<int:job_id>")
    def index(job_id=None):
        return render_template("app/index.html")

    @app.post("/api/jobs")
    def create_job():
        try:
            values = _validate_job_payload(request.get_json(silent=True))
        except ValueError as error:
            return jsonify(success=False, error=str(error)), 400

        job = EmailJob(**values)
        db.session.add(job)
        db.session.commit()
        return jsonify(success=True, job={"id": job.id, "event_name": job.event_name, "status": job.status}), 201

    @app.post("/api/jobs/<int:job_id>/assets")
    def upload_job_assets(job_id):
        job = db.session.get(EmailJob, job_id)
        if job is None:
            return jsonify(success=False, error="Email job not found."), 404

        poster = request.files.get("poster")
        background = request.files.get("background")
        if not any(file and file.filename for file in (poster, background)):
            return jsonify(success=False, error="Provide a poster or background image."), 400

        try:
            poster_url = asset_service.upload_poster(poster) if poster and poster.filename else None
            background_url = asset_service.upload_background(background) if background and background.filename else None
        except asset_service.InvalidAssetError as error:
            return jsonify(success=False, error=str(error)), 400
        except asset_service.AssetServiceError as error:
            return jsonify(success=False, error=str(error)), 502

        if poster_url:
            job.event_poster = poster_url
        if background_url:
            job.email_bg = background_url
        db.session.commit()
        return jsonify(success=True, assets={"poster_url": poster_url, "background_url": background_url})

    @app.post("/api/jobs/<int:job_id>/context/generate")
    def generate_job_context(job_id):
        job = db.session.get(EmailJob, job_id)
        if job is None:
            return jsonify(success=False, error="Email job not found."), 404

        try:
            context = sense_maker.generate_email_context(job)
        except sense_maker.SenseMakerValidationError as error:
            return jsonify(success=False, error=str(error)), 400
        except sense_maker.SenseMakerError as error:
            return jsonify(success=False, error=str(error)), 502

        job.email_context = context
        job.status = JobStatus.CONTEXT_GENERATED
        db.session.commit()
        return jsonify(
            success=True,
            job_id=job.id,
            status=job.status,
            email_context=context,
        )

    @app.put("/api/jobs/<int:job_id>/context")
    def approve_job_context(job_id):
        job = db.session.get(EmailJob, job_id)
        if job is None:
            return jsonify(success=False, error="Email job not found."), 404

        context_payload = request.get_json(silent=True)
        if not isinstance(context_payload, dict):
            return jsonify(success=False, error="Request body must be a JSON object."), 400

        # Store original context and status for rollback on validation failure
        original_context = job.email_context
        original_status = job.status

        try:
            validated_context = EmailContext.model_validate(context_payload).model_dump(mode="json", exclude_defaults=True)
        except Exception as error:
            # Preserve original context and status on validation failure
            job.email_context = original_context
            job.status = original_status
            db.session.commit()
            return jsonify(success=False, error=f"Invalid email context: {str(error)}"), 400

        job.email_context = validated_context
        job.status = JobStatus.CONTEXT_APPROVED
        db.session.commit()
        return jsonify(
            success=True,
            job_id=job.id,
            status=job.status,
            email_context=validated_context,
        )

    @app.post("/api/jobs/<int:job_id>/email/generate")
    def generate_job_email(job_id):
        job = db.session.get(EmailJob, job_id)
        if job is None:
            return jsonify(success=False, error="Email job not found."), 404

        if job.status not in (JobStatus.CONTEXT_APPROVED, JobStatus.EMAIL_RENDERED):
            return jsonify(success=False, error=f"Job must be in CONTEXT_APPROVED or EMAIL_RENDERED state to generate email. Current state: {job.status}"), 400

        if not job.email_context:
            return jsonify(success=False, error="Job has no approved context to render."), 400

        # Store original email_html and status for rollback on rendering failure
        original_email_html = job.email_html
        original_status = job.status

        # Inject organization logo URLs for existing jobs that don't have them
        # This ensures legacy jobs receive the Brahmand email identity
        context_with_logos = job.email_context.copy()
        if not context_with_logos.get('brahmand_logo_url'):
            context_with_logos['brahmand_logo_url'] = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/Brahmand_Logo_-_Black_PNG.png'
        if not context_with_logos.get('snt_logo_url'):
            context_with_logos['snt_logo_url'] = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948490/sntlogo.png'
        if not context_with_logos.get('osail_logo_url'):
            context_with_logos['osail_logo_url'] = 'https://res.cloudinary.com/vmt4lznh/image/upload/v1787948489/Osail_black_logo.png'

        try:
            html = email_maker.render_email(
                context_with_logos,
                poster_url=job.event_poster,
                background_url=job.email_bg,
            )
        except email_maker.EmailMakerError as error:
            # Preserve original email_html and status on rendering failure
            job.email_html = original_email_html
            job.status = original_status
            db.session.commit()
            return jsonify(success=False, error=f"Email rendering failed: {str(error)}"), 500

        job.email_html = html
        job.status = JobStatus.EMAIL_RENDERED
        db.session.commit()
        return jsonify(
            success=True,
            job_id=job.id,
            status=job.status,
            email_html=html,
        )

    @app.post("/api/jobs/<int:job_id>/email/approve")
    def approve_job_email(job_id):
        job = db.session.get(EmailJob, job_id)
        if job is None:
            return jsonify(success=False, error="Email job not found."), 404

        if job.status != JobStatus.EMAIL_RENDERED:
            return jsonify(success=False, error=f"Job must be in EMAIL_RENDERED state to approve email. Current state: {job.status}"), 400

        job.status = JobStatus.EMAIL_APPROVED
        db.session.commit()
        return jsonify(
            success=True,
            job_id=job.id,
            status=job.status,
        )


    @app.put("/api/jobs/<int:job_id>/email/content")
    def update_job_email_content(job_id):
        """Persist a human edit and re-render without changing workflow state."""
        job = db.session.get(EmailJob, job_id)
        if job is None:
            return jsonify(success=False, error="Email job not found."), 404
        if job.status != JobStatus.EMAIL_RENDERED:
            return jsonify(success=False, error=f"Job must be in EMAIL_RENDERED state to edit email. Current state: {job.status}"), 400
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(success=False, error="Request body must be a JSON object."), 400
        try:
            context = EmailContext.model_validate(payload).model_dump(mode="json", exclude_defaults=True)
            html = email_maker.render_email(context, poster_url=job.event_poster, background_url=job.email_bg)
        except Exception as error:
            return jsonify(success=False, error=f"Invalid email content: {str(error)}"), 400
        job.email_context = context
        job.email_html = html
        db.session.commit()
        return jsonify(success=True, job_id=job.id, status=job.status, email_context=context, email_html=html)

    @app.get("/api/jobs/<int:job_id>")
    def get_job(job_id):
        job = db.session.get(EmailJob, job_id)
        if job is None:
            return jsonify(success=False, error="Email job not found."), 404
        return jsonify(success=True, job=job.to_dict())

    @app.get("/api/jobs")
    def list_jobs():
        jobs = db.session.execute(db.select(EmailJob).order_by(EmailJob.id)).scalars()
        return jsonify(success=True, jobs=[job.to_dict() for job in jobs])

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
