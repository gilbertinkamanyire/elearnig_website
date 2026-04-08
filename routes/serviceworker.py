import os, json
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, g, jsonify, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required, role_required, send_notification_email, send_reset_email

def register_serviceworker(app):


    @app.route('/manifest.json')
    def manifest():
        return jsonify({
            "name": "LearnUG - Online Learning",
            "short_name": "LearnUG",
            "description": "Lightweight learning platform for Uganda",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#fffaf5",
            "theme_color": "#f97316",
            "icons": []
        })

    @app.route('/sw.js')
    def sw():
        return send_from_directory('static', 'sw.js')


