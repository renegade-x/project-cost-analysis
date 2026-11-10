from app.extensions import db
from app.models import CostItem, Project, User


def test_password_is_hashed(make_user):
    user = make_user()
    assert user.password_hash != "strong-password"
    assert user.check_password("strong-password")
    assert not user.check_password("wrong")


def test_tables_and_delete_cascade(app, make_user):
    user = make_user()
    with app.app_context():
        project = Project(name="Demo", user_id=user.id)
        project.items.append(CostItem(category="Labour", estimated=10, actual=12))
        db.session.add(project)
        db.session.commit()
        assert db.session.scalar(db.select(CostItem)) is not None
        db.session.delete(project)
        db.session.commit()
        assert db.session.scalar(db.select(CostItem)) is None
        assert db.session.get(User, user.id) is not None
