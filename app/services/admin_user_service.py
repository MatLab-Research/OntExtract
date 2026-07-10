"""Administrative user queries and account state transitions."""

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.term import Term
from app.models.user import User
from app.services.base_service import NotFoundError, PermissionError, ValidationError


class AdminUserService:
    """Manage users while enforcing administrator self-protection rules."""

    @staticmethod
    def list_context(page, status_filter='all', role_filter='all', search_query=''):
        query = User.query
        if status_filter != 'all':
            query = query.filter_by(account_status=status_filter)
        if role_filter == 'admin':
            query = query.filter_by(is_admin=True)
        elif role_filter == 'user':
            query = query.filter_by(is_admin=False)
        if search_query:
            query = query.filter(
                User.username.ilike(f'%{search_query}%')
                | User.email.ilike(f'%{search_query}%')
            )
        pagination = query.order_by(User.created_at.desc()).paginate(
            page=page,
            per_page=20,
            error_out=False,
        )
        return {
            'users': pagination.items,
            'pagination': pagination,
            'status_filter': status_filter,
            'role_filter': role_filter,
            'search_query': search_query,
            'active_page': 'users',
            'page_title': 'User Management',
        }

    @classmethod
    def detail_context(cls, user_id):
        user = cls.get_user(user_id)
        return {
            'user': user,
            'experiments_count': Experiment.query.filter_by(user_id=user_id).count(),
            'documents_count': Document.query.filter_by(user_id=user_id).count(),
            'terms_count': Term.query.filter_by(created_by=user_id).count(),
            'active_page': 'users',
            'page_title': f'User: {user.username}',
        }

    @staticmethod
    def get_user(user_id):
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError('User not found')
        return user

    @classmethod
    def get_edit_context(cls, user_id, actor_id):
        user = cls.get_user(user_id)
        cls._reject_self(
            user,
            actor_id,
            'You cannot edit your own account from this interface',
        )
        return {
            'user': user,
            'active_page': 'users',
            'page_title': f'Edit User: {user.username}',
        }

    @classmethod
    def update_user(cls, user_id, actor_id, is_admin, account_status):
        user = cls.get_user(user_id)
        cls._reject_self(
            user,
            actor_id,
            'You cannot edit your own account from this interface',
        )
        user.is_admin = bool(is_admin)
        if account_status in ('active', 'suspended'):
            user.account_status = account_status
            user.is_active = account_status == 'active'
        db.session.commit()
        return user

    @classmethod
    def set_password(cls, user_id, actor_id, password, confirmation):
        user = cls.get_user(user_id)
        cls._reject_self(
            user,
            actor_id,
            'You cannot set your own password from this interface. '
            'Use the password change feature.',
        )
        if not password or len(password) < 6:
            raise ValidationError('Password must be at least 6 characters long')
        if password != confirmation:
            raise ValidationError('Passwords do not match')
        user.set_password(password)
        db.session.commit()
        return user

    @classmethod
    def toggle_admin(cls, user_id, actor_id):
        user = cls.get_user(user_id)
        cls._reject_self(
            user,
            actor_id,
            'Cannot modify your own admin status',
        )
        user.is_admin = not user.is_admin
        db.session.commit()
        return user

    @classmethod
    def suspend(cls, user_id, actor_id):
        user = cls.get_user(user_id)
        cls._reject_self(
            user,
            actor_id,
            'You cannot suspend your own account',
        )
        user.account_status = 'suspended'
        user.is_active = False
        db.session.commit()
        return user

    @classmethod
    def activate(cls, user_id):
        user = cls.get_user(user_id)
        user.account_status = 'active'
        user.is_active = True
        db.session.commit()
        return user

    @classmethod
    def delete_user(cls, user_id, actor_id):
        user = cls.get_user(user_id)
        cls._reject_self(
            user,
            actor_id,
            'You cannot delete your own account',
        )
        username = user.username
        try:
            db.session.delete(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return username

    @staticmethod
    def make_admin(username):
        user = User.query.filter_by(username=username).first()
        if not user:
            raise NotFoundError('User not found')
        user.is_admin = True
        db.session.commit()
        return user

    @staticmethod
    def _reject_self(user, actor_id, message):
        if user.id == actor_id:
            raise PermissionError(message)
