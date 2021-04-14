from flask import Flask, url_for, redirect, render_template
from flask_login import LoginManager, login_user, logout_user, login_required
from data import db_session
from data.store import Store
from data.category import Category
from data.item import Item
from data.currency import Currency
from data.user import User
from forms.register_form import RegisterForm
from forms.login_form import LoginForm
import random
import json


app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_store_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)
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


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    store_settings = get_store_settings()
    store_settings['title'] = 'Регистрация'
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', form=form,
                                   message="Пароли не совпадают", **store_settings)
        if not form.age.data.isnumeric():
            return render_template('register.html', form=form,
                                   message="Неверный возраст", **store_settings)
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', form=form,
                                   message="Такой пользователь уже есть", **store_settings)
        user = User(
            name=form.name.data,
            email=form.email.data,
            surname=form.surname.data,
            age=int(form.age.data),
            address=form.address.data,
            got_bonus=0
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        with open(f'accounts/user_{user.id}.json', 'w', encoding='utf-8') as jsonfile:
            data = {'shopping_cart': {'items': [], 'summary': {}}, 'orders': {}, 'currencies': dict()}
            for i in db_sess.query(Currency).all():
                data['currencies'][i.id] = 0
            json.dump(data, jsonfile)
        return redirect("/")
    return render_template('register.html', form=form, **store_settings)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    store_settings = get_store_settings()
    store_settings['title'] = 'Вход'
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form, **store_settings)
    return render_template('login.html', form=form, **store_settings)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/refresh')
def refresh():
    set_current_store()
    return redirect('/')


if __name__ == '__main__':
    main()
