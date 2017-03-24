import constants
import db_connection
import models.subscriptions
import models.user
import numbers


def test_get_all():
    s = models.subscriptions.Subscriptions()
    subs = s.get_all()
    assert type(subs) is list
    assert isinstance(subs[0], dict)


def test_get_id_list():
    s = models.subscriptions.Subscriptions()
    ids = s.get_id_list()
    assert type(ids) is list
    assert isinstance(ids[0], numbers.Integral)


def test_get_by_email():
    u = models.user.User()
    s = models.subscriptions.Subscriptions()
    sub = s.get_by_email(u.email)
    assert bool(sub)
    assert sub.plan == 'admin'

    sub = s.get_by_email('test@example.com')
    assert bool(sub)
    assert sub.name == 'Test Sub'


def test_get():
    s = models.subscriptions.Subscriptions()
    ids = s.get_id_list()
    for id in ids:
        sub = s.get(id)
        assert sub is not None