from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.urls import url_parse
import os
from pathlib import Path
from datetime import datetime, timezone
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from dotenv import load_dotenv

from config import Config
from models import db, User, Post, Comment, Tag

load_dotenv()  # Load environment variables from .env file

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'info'

    # Ensure required directories exist
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path('instance').mkdir(exist_ok=True)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.before_request
    def before_request():
        if current_user.is_authenticated:
            current_user.last_seen = datetime.utcnow()
            try:
                db.session.commit()
            except Exception as e:
                app.logger.error(f"Error updating last_seen: {e}")
                db.session.rollback()

    @app.route('/')
    def landing():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        return render_template('landing.html')

    @app.route('/home')
    @login_required
    def home():
        try:
            page = request.args.get('page', 1, type=int)
            category = request.args.get('category')
            sort = request.args.get('sort', 'latest')
            tag = request.args.get('tag')

            # Base query
            query = Post.query

            # Apply filters
            if category and category != 'all':
                query = query.filter_by(category=category)
            if tag:
                query = query.filter(Post.tags.any(name=tag))

            # Apply sorting
            if sort == 'latest':
                query = query.order_by(Post.date_posted.desc())
            elif sort == 'popular':
                query = query.order_by(Post.likes.count().desc())
            elif sort == 'following' and current_user.is_authenticated:
                query = query.join(Post.author).filter(
                    User.followers.any(id=current_user.id)
                )

            # Paginate results
            posts = query.paginate(page=page, per_page=10, error_out=False)

            # Get trending topics
            trending_topics = Tag.query.join(Post.tags).group_by(Tag.id).order_by(
                db.func.count(Post.id).desc()
            ).limit(5).all()

            # Get suggested users
            suggested_users = User.query.filter(
                User.id != current_user.id
            ).order_by(
                db.func.random()
            ).limit(3).all()

            return render_template('home.html',
                                 posts=posts.items,
                                 pagination=posts,
                                 trending_topics=trending_topics,
                                 suggested_users=suggested_users,
                                 sort=sort)

        except Exception as e:
            app.logger.error(f"Error loading home page: {e}")
            flash('An error occurred while loading posts.', 'error')
            return redirect(url_for('landing'))

    @app.route('/profile/<username>')
    @login_required
    def profile(username):
        user = User.query.filter_by(username=username).first_or_404()
        return render_template('profile.html', user=user)

    @app.route('/profile')
    @login_required
    def own_profile():
        return redirect(url_for('profile', username=current_user.username))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        
        if request.method == 'POST':
            try:
                email = request.form.get('email', '').strip()
                password = request.form.get('password', '')
                remember = request.form.get('remember', False) == 'on'
                
                user = User.query.filter_by(email=email).first()
                
                if user and user.check_password(password):
                    login_user(user, remember=remember)
                    next_page = request.args.get('next')
                    if not next_page or url_parse(next_page).netloc != '':
                        next_page = url_for('home')
                    return redirect(next_page)
                else:
                    flash('Invalid email or password', 'error')
            
            except Exception as e:
                app.logger.error(f"Login error: {e}")
                flash('An error occurred during login.', 'error')
        
        return render_template('auth/login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('landing'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        
        if request.method == 'POST':
            try:
                username = request.form.get('username', '').strip()
                email = request.form.get('email', '').strip()
                password = request.form.get('password', '')
                confirm_password = request.form.get('confirm_password', '')

                # Validation
                if not all([username, email, password, confirm_password]):
                    flash('All fields are required.', 'error')
                    return redirect(url_for('register'))

                if password != confirm_password:
                    flash('Passwords do not match.', 'error')
                    return redirect(url_for('register'))

                if User.query.filter_by(username=username).first():
                    flash('Username already taken.', 'error')
                    return redirect(url_for('register'))
                
                if User.query.filter_by(email=email).first():
                    flash('Email already registered.', 'error')
                    return redirect(url_for('register'))
                
                # Create new user
                user = User(username=username, email=email)
                user.set_password(password)
                
                db.session.add(user)
                db.session.commit()
                
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            
            except Exception as e:
                app.logger.error(f"Registration error: {e}")
                db.session.rollback()
                flash('An error occurred during registration.', 'error')
                
        return render_template('auth/register.html')

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    def init_db():
        with app.app_context():
            try:
                db.create_all()
                
                # Create test user if none exists
                if not User.query.first():
                    test_user = User(
                        username='testuser',
                        email='test@example.com'
                    )
                    test_user.set_password('password123')
                    
                    # Create some test tags
                    tags = [
                        Tag(name='python'),
                        Tag(name='javascript'),
                        Tag(name='web'),
                        Tag(name='database')
                    ]
                    
                    # Create a test post
                    post = Post(
                        title='Welcome to Godspeed',
                        content='This is a test post.',
                        author=test_user,
                        tags=tags[:2]  # Add python and javascript tags
                    )
                    
                    db.session.add(test_user)
                    db.session.add_all(tags)
                    db.session.add(post)
                    db.session.commit()
                    print("Test data created successfully!")
                    
            except Exception as e:
                print(f"Database initialization error: {e}")
                db.session.rollback()

    @app.template_filter('timeago')
    def timeago(date):
        """Convert a datetime to a time ago string."""
        now = datetime.now(timezone.utc)
        diff = now - date

        if diff.days > 365:
            return f"{diff.days // 365}y ago"
        elif diff.days > 30:
            return f"{diff.days // 30}mo ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "just now"

    @app.template_filter('markdown')
    def markdown_filter(text):
        """Convert markdown to HTML with syntax highlighting."""
        return markdown.markdown(text, 
                               extensions=['codehilite', 
                                         'fenced_code', 
                                         'tables', 
                                         'nl2br'])

    @app.route('/post/<int:post_id>/like', methods=['POST'])
    @login_required
    def like_post(post_id):
        try:
            post = Post.query.get_or_404(post_id)
            if current_user in post.likes:
                post.likes.remove(current_user)
                liked = False
            else:
                post.likes.append(current_user)
                liked = True
            
            db.session.commit()
            return jsonify({
                'success': True,
                'liked': liked,
                'likes_count': len(post.likes)
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/post/<int:post_id>/bookmark', methods=['POST'])
    @login_required
    def bookmark_post(post_id):
        try:
            post = Post.query.get_or_404(post_id)
            if current_user in post.bookmarks:
                post.bookmarks.remove(current_user)
                bookmarked = False
            else:
                post.bookmarks.append(current_user)
                bookmarked = True
            
            db.session.commit()
            return jsonify({
                'success': True,
                'bookmarked': bookmarked
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/user/<int:user_id>/follow', methods=['POST'])
    @login_required
    def follow_user(user_id):
        try:
            user = User.query.get_or_404(user_id)
            if current_user in user.followers:
                user.followers.remove(current_user)
                following = False
            else:
                user.followers.append(current_user)
                following = True
            
            db.session.commit()
            return jsonify({
                'success': True,
                'following': following
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)})

    return app, init_db

if __name__ == '__main__':
    app, init_db = create_app()
    init_db()
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    )