# routes/assistants.py
from flask import render_template, request, redirect, url_for, flash
from modules import assistant_manager, server_cache, db_backup_recovery

def _invalidate_assistants_cache():
    """Invalidate assistant profile + duty cache lanes."""
    server_cache.invalidate(server_cache.ASSISTANTS_PROFILE_LIST_CACHE_KEY)
    server_cache.invalidate(server_cache.ASSISTANTS_DUTY_LIST_CACHE_KEY)


def register_assistant_routes(app):
    """Register assistant CRUD routes."""
    
    @app.route("/assistants")
    def assistants_list():
        assistants = server_cache.get_or_set(
            server_cache.ASSISTANTS_PROFILE_LIST_CACHE_KEY,
            assistant_manager.get_all_assistants,
            policy="assistant_profile",
        )
        return render_template(
            "assistants.html",
            assistants=assistants,
        )

    @app.route("/assistants/add", methods=["GET", "POST"])
    def assistants_add():
        if request.method == "POST":
            backup_path = db_backup_recovery.create_backup("assistants_add")
            try:
                assistant_manager.add_assistant(
                    request.form["name"],
                    request.form.get("role", ""),
                    request.form.get("email", ""),
                    request.form.get("phone", ""),
                )
                _invalidate_assistants_cache()
                flash("Assistant added successfully.", "success")
            except Exception as e:
                db_backup_recovery.restore_backup(backup_path)
                _invalidate_assistants_cache()
                flash(f"Operation failed. Database was restored from backup. Backup: {backup_path}. Error: {e}", "danger")
            return redirect(url_for("assistants_list"))
        return render_template("assistant_form.html", action="Add", assistant=None)

    @app.route("/assistants/edit/<int:aid>", methods=["GET", "POST"])
    def assistants_edit(aid):
        asst = assistant_manager.get_assistant(aid)
        if not asst:
            return "Assistant not found", 404
        if request.method == "POST":
            backup_path = db_backup_recovery.create_backup("assistants_edit")
            try:
                assistant_manager.update_assistant(
                    aid,
                    request.form["name"],
                    request.form.get("role", ""),
                    request.form.get("email", ""),
                    request.form.get("phone", ""),
                )
                _invalidate_assistants_cache()
                flash("Assistant updated.", "info")
            except Exception as e:
                db_backup_recovery.restore_backup(backup_path)
                _invalidate_assistants_cache()
                flash(f"Operation failed. Database was restored from backup. Backup: {backup_path}. Error: {e}", "danger")
            return redirect(url_for("assistants_list"))
        return render_template("assistant_form.html", action="Edit", assistant=asst)

    @app.route("/assistants/delete/<int:aid>")
    def assistants_delete(aid):
        backup_path = db_backup_recovery.create_backup("assistants_delete")
        try:
            assistant_manager.delete_assistant(aid)
            _invalidate_assistants_cache()
            flash("Assistant deleted.", "warning")
        except Exception as e:
            db_backup_recovery.restore_backup(backup_path)
            _invalidate_assistants_cache()
            flash(f"Operation failed. Database was restored from backup. Backup: {backup_path}. Error: {e}", "danger")
        return redirect(url_for("assistants_list"))
