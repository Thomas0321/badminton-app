from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import re
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
import uuid
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate

# 自動載入 .env 檔案
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from db_autofix import check_and_rebuild_db

# Render 部署會有 /data 目錄，本地則 fallback
if os.path.exists('/data'):
    DB_PATH = '/data/badminton.db'
else:
    DB_PATH = os.path.abspath('./badminton.db')

check_and_rebuild_db(DB_PATH)

app = Flask(__name__)
# --- Render/local 路徑與環境變數設定 ---
import platform

# Render 部署會有 /data 目錄，本地則 fallback
if os.path.exists('/data'):
    DB_PATH = '/data/badminton.db'
    UPLOAD_PATH = '/data/uploads'
else:
    DB_PATH = os.path.abspath('./badminton.db')
    UPLOAD_PATH = os.path.abspath('./uploads')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['UPLOAD_FOLDER'] = UPLOAD_PATH

# SECRET_KEY 必須設在環境變數（Render dashboard 設定）
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError('SECRET_KEY 環境變數未設定！請在 Render 或本地設置。')

# 自動建立 uploads 資料夾
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

@app.context_processor
def inject_user():
    current_user = None
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
    
    csrf_token = secrets.token_hex(16)
    session['csrf_token'] = csrf_token
    
    return dict(current_user=current_user, csrf_token=csrf_token)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)  # 新增帳號欄位
    password_hash = db.Column(db.String(128), nullable=False)  # 新增密碼欄位
    nickname = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)  # 新增電話欄位
    gender = db.Column(db.String(10), nullable=False)
    experience_years = db.Column(db.Integer, nullable=False)
    preferred_position = db.Column(db.String(50), nullable=False)
    skill_level = db.Column(db.Integer, nullable=False)  # 技術等級 1~18
    play_style = db.Column(db.String(20), nullable=False, default='防守型')  # 擅長打法：雙打/單打/都可以
    preferred_time = db.Column(db.String(50), nullable=False)  # 偏好時段
    bio = db.Column(db.Text)  # 自我介紹
    contact = db.Column(db.String(100), nullable=False)  # 聯絡方式
    preferred_region = db.Column(db.String(50), nullable=False)  # 偏好地區
    notification_enabled = db.Column(db.Boolean, default=True)  # 通知設定
    ban_until = db.Column(db.DateTime)  # 禁令到期時間

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_city = db.Column(db.String(50), nullable=False)
    location_venue = db.Column(db.String(100), nullable=False)
    location_address = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    max_participants = db.Column(db.Integer, default=4)
    activity_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    cover_image = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    organizer = db.relationship('User', backref='organized_teams')

class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_waitlist = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    team = db.relationship('Team', backref='members')
    user = db.relationship('User', backref='team_memberships')

class TeamMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    team = db.relationship('Team', backref='messages')
    user = db.relationship('User', backref='messages')

class Cancellation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    cancelled_at = db.Column(db.DateTime, default=datetime.utcnow)
    hours_before_event = db.Column(db.Float, nullable=False)
    
    user = db.relationship('User', backref='cancellations')
    team = db.relationship('Team', backref='cancellations')

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/teams')
def teams():
    city = request.args.get('city', '')
    venue = request.args.get('venue', '')
    skill_level = request.args.get('skill_level', '')
    time_period = request.args.get('time_period', '')
    
    query = Team.query
    
    if city:
        query = query.filter(Team.location_city.contains(city))
    if venue:
        query = query.filter(Team.location_venue.contains(venue))
    if skill_level:
        query = query.filter(Team.activity_type.contains(skill_level))
    
    teams = query.filter(Team.start_time > datetime.utcnow()).all()
    
    team_data = []
    for team in teams:
        current_members = TeamMember.query.filter_by(team_id=team.id, is_waitlist=False).count()
        waitlist_count = TeamMember.query.filter_by(team_id=team.id, is_waitlist=True).count()
        
        team_data.append({
            'id': team.id,
            'name': team.name,
            'organizer': team.organizer.nickname,
            'organizer_gender': team.organizer.gender,
            'organizer_skill_level': team.organizer.skill_level,
            'location_city': team.location_city,
            'location_venue': team.location_venue,
            'location_address': team.location_address,
            'start_time': team.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': team.end_time.strftime('%Y-%m-%d %H:%M'),
            'activity_type': team.activity_type,
            'current_members': current_members,
            'max_participants': team.max_participants,
            'waitlist_count': waitlist_count,
            'description': team.description,
            'cover_image': team.cover_image
        })
    
    return jsonify(team_data)

@app.route('/create_team', methods=['GET', 'POST'])
def create_team():
    if 'user_id' not in session:
        return redirect(url_for('profile_setup'))
    
    user = User.query.get(session['user_id'])
    if user.ban_until and user.ban_until > datetime.utcnow():
        return jsonify({'error': '您目前被禁止建立隊伍，請等待禁令解除'}), 403
    
    if request.method == 'POST':
        data = request.get_json()
        
        team = Team(
            name=data['name'],
            organizer_id=session['user_id'],
            location_city=data['location_city'],
            location_venue=data['location_venue'],
            location_address=data['location_address'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']),
            max_participants=min(int(data['max_participants']), 4),
            activity_type=data['activity_type'],
            description=data.get('description', '')
        )
        
        db.session.add(team)
        db.session.commit()
        
        # Automatically add organizer as first member
        member = TeamMember(team_id=team.id, user_id=session['user_id'])
        db.session.add(member)
        db.session.commit()
        
        return jsonify({'success': True, 'team_id': team.id})
    
    return render_template('create_team.html')

@app.route('/join_team/<int:team_id>', methods=['POST'])
def join_team(team_id):
    if 'user_id' not in session:
        return jsonify({'error': '請先設定個人檔案'}), 401
    
    user = User.query.get(session['user_id'])
    if user.ban_until and user.ban_until > datetime.utcnow():
        return jsonify({'error': '您目前被禁止參加活動，請等待禁令解除'}), 403
    
    team = Team.query.get_or_404(team_id)
    
    # 新增：活動開始前2小時禁止加入
    now = datetime.utcnow()
    if (team.start_time - now).total_seconds() < 2 * 3600:
        return jsonify({'error': '距離活動開始已不足2小時，無法再加入此隊伍'}), 403
    
    # Check if already a member
    existing_member = TeamMember.query.filter_by(team_id=team_id, user_id=session['user_id']).first()
    if existing_member:
        return jsonify({'error': '您已經是此隊伍的成員'}), 400
    
    current_members = TeamMember.query.filter_by(team_id=team_id, is_waitlist=False).count()
    
    is_waitlist = current_members >= team.max_participants
    
    member = TeamMember(
        team_id=team_id,
        user_id=session['user_id'],
        is_waitlist=is_waitlist
    )
    
    db.session.add(member)
    db.session.commit()
    
    status = '候補' if is_waitlist else '成功加入'
    return jsonify({'success': True, 'status': status})

# 自動清理過期隊伍（活動結束後自動刪除隊伍與成員、留言等）
def clean_expired_teams():
    now = datetime.utcnow()
    expired_teams = Team.query.filter(Team.end_time < now).all()
    for team in expired_teams:
        # 刪除隊伍成員
        TeamMember.query.filter_by(team_id=team.id).delete()
        # 刪除隊伍留言
        TeamMessage.query.filter_by(team_id=team.id).delete()
        # 刪除隊伍本身
        db.session.delete(team)
    db.session.commit()


@app.route('/leave_team/<int:team_id>', methods=['POST'])
def leave_team(team_id):
    if 'user_id' not in session:
        return jsonify({'error': '請先登入'}), 401
    
    team = Team.query.get_or_404(team_id)
    member = TeamMember.query.filter_by(team_id=team_id, user_id=session['user_id']).first()
    
    if not member:
        return jsonify({'error': '您不是此隊伍的成員'}), 400
    
    # Check if cancellation is within 24 hours
    hours_before = (team.start_time - datetime.utcnow()).total_seconds() / 3600
    
    if hours_before < 24 and not member.is_waitlist:
        # Apply penalty
        user = User.query.get(session['user_id'])
        user.cancellation_count += 1
        user.ban_until = datetime.utcnow() + timedelta(days=7)
        
        cancellation = Cancellation(
            user_id=session['user_id'],
            team_id=team_id,
            hours_before_event=hours_before
        )
        db.session.add(cancellation)
    
    db.session.delete(member)
    
    # Promote waitlist member if needed
    if not member.is_waitlist:
        waitlist_member = TeamMember.query.filter_by(team_id=team_id, is_waitlist=True).order_by(TeamMember.joined_at).first()
        if waitlist_member:
            waitlist_member.is_waitlist = False
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/team/<int:team_id>')
def team_detail(team_id):
    team = Team.query.get_or_404(team_id)
    members = TeamMember.query.filter_by(team_id=team_id, is_waitlist=False).all()
    waitlist = TeamMember.query.filter_by(team_id=team_id, is_waitlist=True).all()
    messages = TeamMessage.query.filter_by(team_id=team_id, is_public=True).order_by(TeamMessage.created_at.desc()).all()
    
    from datetime import timedelta
    return render_template('team_detail.html', team=team, members=members, waitlist=waitlist, messages=messages, timedelta=timedelta)

@app.route('/team/<int:team_id>/messages', methods=['GET', 'POST'])
def team_messages(team_id):
    if request.method == 'POST':
        if 'user_id' not in session:
            return jsonify({'error': '請先登入'}), 401
        
        data = request.get_json()
        message = TeamMessage(
            team_id=team_id,
            user_id=session['user_id'],
            message=data['message'],
            is_public=data.get('is_public', True)
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({'success': True})
    
    # GET request
    is_public = request.args.get('public', 'true').lower() == 'true'
    messages = TeamMessage.query.filter_by(team_id=team_id, is_public=is_public).order_by(TeamMessage.created_at.desc()).all()
    
    message_data = []
    for msg in messages:
        message_data.append({
            'id': msg.id,
            'user_nickname': msg.user.nickname,
            'message': msg.message,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return jsonify(message_data)

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    memberships = TeamMember.query.filter_by(user_id=user.id).join(Team).order_by(Team.start_time.desc()).all()
    return render_template('user_profile.html', user=user, memberships=memberships)

# ====== 註冊、登入、登出功能 ======

@app.route('/profile_setup', methods=['GET', 'POST'])
def profile_setup():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        data = request.get_json()
        # Optional phone update validation if provided
        if data and 'phone' in data and data['phone']:
            digits_only = re.sub(r'\D', '', data['phone'])
            if len(digits_only) != 10:
                return jsonify({'success': False, 'error': '電話需為10位數字（例如：0912345678）'}), 400
            user.phone = digits_only
        user.nickname = data.get('nickname', user.nickname)
        user.gender = data.get('gender', user.gender)
        user.experience_years = int(data.get('experience_years', user.experience_years))
        user.preferred_position = data.get('preferred_position', user.preferred_position)
        user.skill_level = int(data.get('skill_level', user.skill_level))
        user.play_style = data.get('play_style', user.play_style or '防守型')
        user.preferred_time = data.get('preferred_time', user.preferred_time)
        user.preferred_region = data.get('preferred_region', user.preferred_region)
        user.contact = data.get('contact', user.contact)
        user.bio = data.get('bio', user.bio)
        user.notification_enabled = bool(data.get('notification_enabled', True))
        db.session.commit()
        return jsonify({'success': True})
    return render_template('profile_setup.html', user=user)

from flask import flash

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        nickname = request.form['nickname'].strip()
        phone = request.form['phone'].strip()
        gender = request.form['gender']
        experience_years = request.form['experience_years']
        preferred_position = request.form['preferred_position']
        skill_level = request.form['skill_level']
        preferred_region = request.form['preferred_region']
        notification_enabled = request.form.get('notification_enabled') == 'on'
        
        if User.query.filter_by(username=username).first():
            flash('帳號已被註冊，請換一個', 'danger')
            return render_template('register.html')
        
        # 驗證電話必須為10碼數字（允許輸入中有非數字符號，但最終僅計算數字）
        digits_only = re.sub(r'\D', '', phone)
        if len(digits_only) != 10:
            flash('電話需為10位數字，請重新輸入（例如：0912345678）', 'danger')
            return render_template('register.html')
        
        user = User(
            username=username,
            nickname=nickname,
            phone=digits_only,
            gender=gender,
            experience_years=int(experience_years),
            preferred_position=preferred_position,
            skill_level=skill_level,
            play_style=request.form.get('play_style', '防守型'),
            preferred_time=request.form.get('preferred_time', '晚上'),
            bio=request.form.get('bio', ''),
            contact=request.form.get('contact', ''),
            preferred_region=preferred_region,
            notification_enabled=notification_enabled
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        flash('註冊成功，已自動登入！', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('查無此帳號，請先註冊', 'danger')
        elif user.check_password(password):
            session['user_id'] = user.id
            flash('登入成功！', 'success')
            return redirect(url_for('index'))
        else:
            flash('帳號或密碼錯誤', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('已登出', 'info')
    return redirect(url_for('login'))

# 查看自己已報名的隊伍
@app.route('/my_teams')
def my_teams():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    memberships = TeamMember.query.filter_by(user_id=user_id).join(Team).order_by(Team.start_time.desc()).all()
    # memberships: List[TeamMember]，每個有 team, is_waitlist
    return render_template('my_teams.html', memberships=memberships)


# Render/gunicorn 會自動以 app:app 啟動
# 確保 /data/uploads 資料夾存在且可寫入

# 不論本地或 Render，每次啟動都自動建立資料表（若尚未建立）
with app.app_context():
    db.create_all()

# 若本地開發自動啟動 Flask 伺服器
if __name__ == '__main__':
    # 依環境變數控制 debug（預設為 False）。雲端以 gunicorn 啟動，不會執行此段。
    debug_flag = os.environ.get('FLASK_DEBUG', '0') in ('1', 'true', 'True')
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=debug_flag)
