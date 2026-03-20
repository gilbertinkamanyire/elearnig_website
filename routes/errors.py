import os, json
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, g, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required, role_required, send_notification_email, send_reset_email

def register_errors(app):


    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500


