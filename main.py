from flask import Flask, url_for, redirect, render_template
from data import db_session
from data.store import Store
from data.category import Category
from data.item import Item
from data.currency import Currency
from data.user import User
import random


app = Flask(__name__)
db_session.global_init("db/store_database.db")
store = Store()


def set_current_store():
    global store
    session = db_session.create_session()
    stores = session.query(Store).all()
    store = random.choice(stores)


def get_store_settings():
    store_settings = dict()
    store_settings['title'] = store.name
    store_settings['slogan'] = store.slogan
    store_settings['logotype'] = url_for('static', filename=f'img/logotypes/{store.logotype}')
    store_settings['icon'] = url_for('static', filename=f'img/icons/{store.icon}')
    return store_settings


def main():
    set_current_store()
    app.run(port=8080, host='127.0.0.1')


@app.route('/')
def main_menu():
    session = db_session.create_session()
    store_settings = get_store_settings()
    items = session.query(Item).all()
    random.shuffle(items)
    special_offer = items.pop()
    special_offer.photo_name = url_for('static', filename=f'img/items/{special_offer.photo_name}')
    special_offer.description = special_offer.description.split(';')[0]
    items = {
        'items': items,
        'length': len(items) // 3
    }
    return render_template('main_page.html', special_offer=special_offer, items=items, **store_settings)


@app.route('/item/<int:item_id>')
def item_page(item_id):
    store_settings = get_store_settings()
    session = db_session.create_session()
    item = session.query(Item).get(item_id)
    if not item:
        store_settings['title'] = '?????????'
        return render_template('item_not_found.html', **store_settings)
    else:
        item_info = dict()
        item_info['item_id'] = item_id
        item_info['name'] = item.name
        item_info['source'] = url_for('static', filename=f'img/items/{item.photo_name}')
        store_settings['title'] = item.name
        item_info['properties'] = item.description.split(';')
        if item.special_price:
            item_info['price'] = item.special_price
            currency = session.query(Currency).get(item.special_currency)
        else:
            item_info['price'] = random.randint(0, 99999999)
            item_info['price'] /= 10 ** random.randint(0, len(str(item_info['price'])))
            currency = random.choice(session.query(Currency).all())
        item_info['currency_id'] = currency.id
        item_info['currency'] = url_for('static', filename=f'img/currencies/'f'{currency.logotype}')
        if random.randint(1, 10) == 10:
            item_info['discount'] = random.randint(1, 400)
            item_info['discount_price'] = item_info['price'] - item_info['price'] * item_info['discount'] / 100
            if currency.is_integer:
                item_info['price'] = int(item_info['price'])
                item_info['discount_price'] = int(item_info['discount_price'])
        else:
            item_info['discount_price'] = None
            item_info['discount'] = None
        return render_template('item_page.html', **store_settings, **item_info)


@app.route('/refresh')
def refresh():
    set_current_store()
    return redirect('/')


if __name__ == '__main__':
    main()
