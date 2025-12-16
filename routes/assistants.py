# routes/assistants.py
from flask import render_template, request, redirect, url_for, flash
from modules import assistant_manager

def register_assistant_routes(app):
    """Register assistant CRUD routes."""
    
    @app.route("/assistants")
    def assistants_list():
        return render_template(
            "assistants.html",
            assistants=assistant_manager.get_all_assistants(),
        )

    @app.route("/assistants/add", methods=["GET", "POST"])
    def assistants_add():
        if request.method == "POST":
            assistant_manager.add_assistant(
                request.form["name"],
                request.form.get("role", ""),
                request.form.get("email", ""),
                request.form.get("phone", ""),
            )
            flash("Assistant added successfully.", "success")
            return redirect(url_for("assistants_list"))
        return render_template("assistant_form.html", action="Add", assistant=None)

    @app.route("/assistants/edit/<int:aid>", methods=["GET", "POST"])
    def assistants_edit(aid):
        asst = assistant_manager.get_assistant(aid)
        if not asst:
            return "Assistant not found", 404
        if request.method == "POST":
            assistant_manager.update_assistant(
                aid,
                request.form["name"],
                request.form.get("role", ""),
                request.form.get("email", ""),
                request.form.get("phone", ""),
            )
            flash("Assistant updated.", "info")
            return redirect(url_for("assistants_list"))
        return render_template("assistant_form.html", action="Edit", assistant=asst)

    @app.route("/assistants/delete/<int:aid>")
    def assistants_delete(aid):
        assistant_manager.delete_assistant(aid)
        flash("Assistant deleted.", "warning")
        return redirect(url_for("assistants_list"))
