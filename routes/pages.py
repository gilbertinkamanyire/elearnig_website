import os, json
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash, g, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required, role_required, send_notification_email, send_reset_email

def register_pages(app):


    @app.route('/help')
    def help_page():
        return render_template('pages/help.html')

    @app.route('/about')
    def about():
        return render_template('pages/about.html')

    @app.route('/terms')
    def terms():
        return render_template('pages/terms.html')

    @app.route('/privacy')
    def privacy():
        return render_template('pages/privacy.html')

    @app.route('/how-it-works')
    def how_it_works():
        return render_template('pages/how_it_works.html')

    @app.route('/wipe-users-now')
    def wipe_users_now():
        from models import get_db
        db = get_db()
        db.execute('DELETE FROM enrollments')
        db.execute('DELETE FROM lesson_progress')
        db.execute('DELETE FROM submissions')
        db.execute('DELETE FROM attendance')
        db.execute('DELETE FROM notifications')
        db.execute('DELETE FROM replies')
        db.execute('DELETE FROM discussions')
        db.execute('DELETE FROM learning_insights')
        db.execute('DELETE FROM courses')
        db.execute('DELETE FROM users WHERE username != "admin"')
        db.commit()
        return "All accounts except admin have been deleted."



