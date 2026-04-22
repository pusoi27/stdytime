# routes/assistants.py
from flask import render_template, request, redirect, url_for, flash
from modules import assistant_manager, server_cache, db_backup_recovery, auth_manager
from routes.auth import require_login, require_admin, require_feature
from routes.operation_utils import flash_scoped_failure, invalidate_scoped_cache


def _assistants_profile_cache_key(owner_user_id: int) -> str:
    return f"{server_cache.ASSISTANTS_PROFILE_LIST_CACHE_KEY}:u:{owner_user_id}"


def _assistants_duty_cache_key(owner_user_id: int) -> str:
    return f"{server_cache.ASSISTANTS_DUTY_LIST_CACHE_KEY}:u:{owner_user_id}"


def _invalidate_assistants_cache(owner_user_id: int):
    """Invalidate assistant profile + duty cache lanes."""
    server_cache.invalidate(_assistants_profile_cache_key(owner_user_id))
    server_cache.invalidate(_assistants_duty_cache_key(owner_user_id))


def register_assistant_routes(app):
    """Register assistant CRUD routes."""
    
    @app.route("/assistants")
    @require_login
    @require_feature(auth_manager.FEATURE_ASSISTANTS)
    def assistants_list():
        owner_user_id = auth_manager.get_current_user_id()

        assistants = server_cache.get_or_set(
            _assistants_profile_cache_key(owner_user_id),
            lambda: assistant_manager.get_all_assistants(owner_user_id=owner_user_id),
            policy="assistant_profile",
        )
        return render_template(
            "assistants.html",
            assistants=assistants,
        )

    @app.route("/assistants/add", methods=["GET", "POST"])
    @require_login
    @require_feature(auth_manager.FEATURE_ASSISTANTS)
    def assistants_add():
        owner_user_id = auth_manager.get_current_user_id()

        if request.method == "POST":
            backup_path = db_backup_recovery.create_backup("assistants_add")
            try:
                assistant_manager.add_assistant(
                    request.form["name"],
                    request.form.get("role", ""),
                    request.form.get("email", ""),
                    request.form.get("phone", ""),
                    owner_user_id=owner_user_id,
                )
                invalidate_scoped_cache(lambda: _invalidate_assistants_cache(owner_user_id))
                flash("Staff member added successfully.", "success")
            except Exception as e:
                flash_scoped_failure(
                    backup_path=backup_path,
                    owner_user_id=owner_user_id,
                    table_names=("staff",),
                    error=e,
                    invalidators=(lambda: _invalidate_assistants_cache(owner_user_id),),
                )
            return redirect(url_for("assistants_list"))
        return render_template("assistant_form.html", action="Add", assistant=None)

    @app.route("/assistants/edit/<int:aid>", methods=["GET", "POST"])
    @require_login
    @require_feature(auth_manager.FEATURE_ASSISTANTS)
    def assistants_edit(aid):
        owner_user_id = auth_manager.get_current_user_id()
        asst = assistant_manager.get_assistant(aid, owner_user_id=owner_user_id)
        if not asst:
            return "Staff member not found", 404
        if request.method == "POST":
            backup_path = db_backup_recovery.create_backup("assistants_edit")
            try:
                assistant_manager.update_assistant(
                    aid,
                    request.form["name"],
                    request.form.get("role", ""),
                    request.form.get("email", ""),
                    request.form.get("phone", ""),
                    owner_user_id=owner_user_id,
                )
                invalidate_scoped_cache(lambda: _invalidate_assistants_cache(owner_user_id))
                flash("Staff member updated.", "info")
            except Exception as e:
                flash_scoped_failure(
                    backup_path=backup_path,
                    owner_user_id=owner_user_id,
                    table_names=("staff",),
                    error=e,
                    invalidators=(lambda: _invalidate_assistants_cache(owner_user_id),),
                )
            return redirect(url_for("assistants_list"))
        return render_template("assistant_form.html", action="Edit", assistant=asst)

    @app.route("/assistants/delete/<int:aid>", methods=["POST"])
    @require_admin
    @require_feature(auth_manager.FEATURE_ASSISTANTS)
    def assistants_delete(aid):
        owner_user_id = auth_manager.get_current_user_id()

        backup_path = db_backup_recovery.create_backup("assistants_delete")
        try:
            assistant_manager.delete_assistant(aid, owner_user_id=owner_user_id)
            invalidate_scoped_cache(lambda: _invalidate_assistants_cache(owner_user_id))
            flash("Staff member deleted.", "warning")
        except Exception as e:
            flash_scoped_failure(
                backup_path=backup_path,
                owner_user_id=owner_user_id,
                table_names=("staff",),
                error=e,
                invalidators=(lambda: _invalidate_assistants_cache(owner_user_id),),
            )
        return redirect(url_for("assistants_list"))
