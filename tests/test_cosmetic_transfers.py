from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from aiohttp import web

from galerazo_bot.database import Database
from galerazo_bot import cosmetic_inventory
from galerazo_bot.mini_app import MiniAppApi, build_mini_app
from tests.test_mini_app import request_stub, signed_init_data
from tests.test_club_rewards import pay, day


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / 'gifts.sqlite3')


def grant(db, owner='1', item='mini'):
    db.grant_paid_hisopo(recipient_user_id=owner, hisopo_key=item, gifted_by_user_id='9')


def quantity(db, owner, item='mini'):
    return sum(row.quantity for row in db.get_paid_hisopo_ownership(owner) if row.hisopo_key == item)


def send(db, recipient='2', request='request-one-123456', sender='1', item='mini'):
    db.transfer_paid_hisopo(sender_user_id=sender, recipient_user_id=recipient, hisopo_key=item, request_id=request)


def purchase(db, charge='purchase-one', owner='1'):
    return db.record_star_payment(telegram_payment_charge_id=charge, provider_payment_charge_id=None,
        user_id='9', recipient_user_id=owner, kind='product', item_key='mini', amount_stars=10,
        currency='XTR', invoice_payload='fixture', source_chat_id=None, reward_hisopo_key='mini',
        paid_at='2026-10-28T12:00:00+00:00')


def test_transfer_moves_one_global_unit_and_retry_is_durable(db):
    grant(db)
    grant(db)
    send(db)
    assert [quantity(db, owner) for owner in ('1','2')] == [1,1]
    send(Database(db.path))
    assert [quantity(db, owner) for owner in ('1','2')] == [1,1]
    send(db, request='request-two-123456')
    assert [quantity(db, owner) for owner in ('1','2')] == [0,2]
    with db._connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM cosmetic_transfers').fetchone()[0] == 2
        assert conn.execute('SELECT COUNT(*) FROM star_payments').fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM paid_hisopo_gifts').fetchone()[0] == 2
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_invalid_transfer_changes_nothing_and_failed_requests_can_retry(db):
    for recipient in ('1','2'):
        with pytest.raises(ValueError, match='gift_self' if recipient=='1' else 'gift_unavailable'):
            send(db, recipient)
    assert db.get_user('2') is None
    grant(db)
    send(db)
    with pytest.raises(ValueError, match='gift_conflict'):
        send(db, '3')
    with pytest.raises(ValueError, match='gift_conflict'):
        send(db, item='pico')
    assert quantity(db, '2') == 1
    assert db.get_user('3') is None


def test_stale_provenance_never_spends_a_missing_unit(db):
    grant(db)
    with db._connect() as conn:
        conn.execute("DELETE FROM paid_hisopo_ownership WHERE user_id='1'")
    with pytest.raises(ValueError, match='gift_unavailable'):
        send(db)
    assert quantity(db,'2') == 0


def test_overflow_is_atomic_and_quantities_keep_integer_precision(db):
    grant(db)
    grant(db, owner='2')
    with db._connect() as conn:
        conn.execute('UPDATE paid_hisopo_ownership SET quantity=? WHERE user_id=?', (cosmetic_inventory.MAX_QUANTITY,'2'))
        conn.execute('UPDATE cosmetic_lots SET quantity=? WHERE owner_id=?', (cosmetic_inventory.MAX_QUANTITY,'2'))
    with pytest.raises(ValueError, match='gift_full'):
        send(db)
    assert quantity(db,'1') == 1
    send(db, sender='2', recipient='3')
    assert quantity(db,'2') == cosmetic_inventory.MAX_QUANTITY-1
    send(db)
    assert quantity(db,'2') == cosmetic_inventory.MAX_QUANTITY
    with db._connect() as conn:
        assert conn.execute("SELECT typeof(quantity) FROM paid_hisopo_ownership WHERE user_id='2'").fetchone()[0] == 'integer'


def test_concurrent_requests_cannot_spend_the_same_unit(db):
    grant(db)
    def attempt(i):
        try:
            send(db, recipient=str(i+2), request=f'request-12345678-{i}')
            return True
        except ValueError as exc:
            assert str(exc) == 'gift_unavailable'
            return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(attempt, range(4))) == 1
    assert sum(quantity(db,str(i)) for i in range(1,6)) == 1
    grant(db)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: send(db,request='identical-123456789'), range(4)))
    assert sum(quantity(db,str(i)) for i in range(1,6)) == 2


def test_payment_refund_follows_transfers_and_preserves_independent_gifts(db):
    purchase(db)
    grant(db, owner='3')
    send(db)
    send(db, sender='2', recipient='3')
    assert quantity(db,'3') == 2
    assert db.refund_star_payment('purchase-one', refunded_at='2026-10-28T13:00:00+00:00')
    assert quantity(db,'3') == 1
    assert not db.refund_star_payment('purchase-one', refunded_at='2026-10-28T13:00:00+00:00')
    assert quantity(db,'1') == quantity(db,'2') == 0


def test_club_rewards_stay_earned_after_gifting_and_refunds_revoke_only_reward(db):
    for index in range(6):
        pay(db,index)
    assert db.reconcile_club_rewards(now=day(180)) == 2
    grant(db, owner='2', item='stellar')
    send(db,item='stellar')
    send(db,item='stellar',recipient='3',request='request-two-123456')
    assert db.reconcile_club_rewards(now=day(180)) == 0
    # One block remains until a second gap interrupts the remaining streak.
    assert db.refund_star_payment('club-1-1', refunded_at=day(181).isoformat())
    assert quantity(db,'2','stellar') == 1
    assert quantity(db,'3','stellar') == 1
    assert db.refund_star_payment('club-1-4', refunded_at=day(182).isoformat())
    assert quantity(db,'3','stellar') == 0
    assert quantity(db,'1','stellar') == 0


def test_migration_preserves_legacy_paid_and_club_inventory_without_repeating(db):
    purchase(db)
    purchase(db,charge='purchase-two')
    grant(db,item='pico')
    for index in range(3):
        pay(db,index)
    db.reconcile_club_rewards(now=day(90))
    grant(db,item='stellar')
    grant(db,owner='2',item='stellar')
    with db._connect() as conn:
        conn.execute('DROP TABLE cosmetic_lots')
        # Legacy inconsistencies must never create more units than the inventory.
        conn.execute("UPDATE paid_hisopo_ownership SET quantity=1 WHERE user_id='1' AND hisopo_key='mini'")
    restarted=Database(db.path)
    assert quantity(restarted,'1','mini') == 1
    assert quantity(restarted,'1','stellar') == 2
    with restarted._connect() as conn:
        lots=[tuple(row) for row in conn.execute('SELECT owner_id,item_key,source,quantity FROM cosmetic_lots ORDER BY 1,2,3')]
        assert len(lots) == 5
        assert ('1','stellar','club:1',1) in lots
        assert ('1','stellar','legacy:1',1) in lots
        cosmetic_inventory.revoke(conn,'stellar','club:1',2,'now')
        cosmetic_inventory.revoke(conn,'mini','payment:missing',1,'now')
    Database(db.path)
    assert quantity(restarted,'1','stellar') == 1
    assert quantity(restarted,'2','stellar') == 1


def api(db):
    return MiniAppApi(db=db, bot_token='99:test-token', bot=None, public_url='https://galerazo.com/miniapp')


def request(body, init_data=None, **kwargs):
    return request_stub(headers={'X-Telegram-Init-Data': signed_init_data('99:test-token') if init_data is None else init_data}, body=body, **kwargs)


BODY={'item_key':'mini','recipient':'2','request_id':'request-one-123456'}


def test_api_recipient_alias_id_canonicalization_and_no_payment(db):
    db.get_or_create_user('2','Recipient','recipient_alias', is_bot=False)
    grant(db)
    response=asyncio.run(api(db).transfer_cosmetic(request({**BODY,'recipient':'@recipient_alias'})))
    assert json.loads(response.text) == {'transferred':True,'recipient_user_id':'2'}
    assert quantity(db,'1') == 0 and quantity(db,'2') == 1
    response=asyncio.run(api(db).transfer_cosmetic(request(BODY)))
    assert response.status == 200
    assert quantity(db,'2') == 1
    grant(db)
    response=asyncio.run(api(db).transfer_cosmetic(request({**BODY,'request_id':'request-two-123456','recipient':'0001'})))
    assert json.loads(response.text) == {'error':'gift_self'}
    assert response.status == 409
    assert quantity(db,'1') == 1


@pytest.mark.parametrize('body', [None,[],{}, {**BODY,'sender_id':'2'}, {**BODY,'recipient':None},
    {**BODY,'recipient':''}, {**BODY,'item_key':[]}, {**BODY,'item_key':'common'}, {**BODY,'request_id':1},
    {**BODY,'request_id':'short'}, {**BODY,'recipient':0}, {**BODY,'recipient':'@unknown_alias'},
    {**BODY,'recipient':'-1'}, {**BODY,'recipient':str(2**63)}, {**BODY,'recipient':'99'}])
def test_api_rejects_invalid_requests_without_moving_inventory(db,body):
    grant(db)
    with pytest.raises(web.HTTPBadRequest):
        asyncio.run(api(db).transfer_cosmetic(request(body)))
    assert quantity(db,'1') == 1


def test_api_authentication_blacklist_conflict_and_routes(db):
    with pytest.raises(web.HTTPUnauthorized):
        asyncio.run(api(db).transfer_cosmetic(request(BODY,init_data='invalid')))
    with pytest.raises(web.HTTPBadRequest):
        asyncio.run(api(db).transfer_cosmetic(request(BODY,json_error=json.JSONDecodeError('bad','',0))))
    db.get_or_create_user('1')
    db.block_user('1','9')
    with pytest.raises(web.HTTPForbidden):
        asyncio.run(api(db).transfer_cosmetic(request(BODY)))
    db.unblock_user('1')
    db.get_or_create_user('2', is_bot=False)
    response=asyncio.run(api(db).transfer_cosmetic(request(BODY)))
    assert response.status == 409
    assert json.loads(response.text)['error'] == 'gift_unavailable'
    app=build_mini_app(db=db,bot_token='99:test-token',bot=None,public_url='https://galerazo.com/miniapp')
    assert any(route.method=='POST' and route.resource.canonical=='/api/gift' for route in app.router.routes())


def test_bot_and_unverified_recipients_never_receive_or_consume_inventory(db):
    grant(db)
    assert db.get_user_bot_status('2') is None
    for recipient in ('2', '@robot_fixture'):
        db.get_or_create_user('3', 'Robot', 'robot_fixture', is_bot=True)
        response=asyncio.run(api(db).transfer_cosmetic(request({**BODY,'recipient':recipient})))
        assert response.status == 409
        assert json.loads(response.text)['error'] == ('gift_unverified' if recipient=='2' else 'gift_bot')
        assert quantity(db,'1') == 1
    # Bot status is not guessed from a username suffix and survives unrelated updates.
    db.get_or_create_user('3', 'Robot renamed')
    assert db.get_user_bot_status('3') is True
    response=asyncio.run(api(db).transfer_cosmetic(request({**BODY,'recipient':'3'})))
    assert json.loads(response.text)['error'] == 'gift_bot'
    db.get_or_create_user('2', 'Human', 'human_ends_bot', is_bot=False)
    response=asyncio.run(api(db).transfer_cosmetic(request({**BODY,'recipient':'@human_ends_bot'})))
    assert response.status == 200
    assert quantity(db,'2') == 1 and quantity(db,'1') == 0


def test_miniapp_does_not_accept_a_signed_bot_as_a_human(db):
    init_data=signed_init_data('99:test-token', user={'id':3,'first_name':'Robot','is_bot':True})
    with pytest.raises(web.HTTPUnauthorized):
        asyncio.run(api(db).transfer_cosmetic(request(BODY,init_data=init_data)))
    assert db.get_user_bot_status('3') is None
