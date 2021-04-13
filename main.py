from flask import Flask, url_for, redirect, render_template
from data import db_session
from data.store import Store
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
    store_settings = get_store_settings()
    return render_template('base.html', **store_settings)


@app.route('/refresh')
def refresh():
    set_current_store()
    return redirect('/')


if __name__ == '__main__':
    main()
