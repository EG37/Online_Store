from flask import Flask, url_for, redirect, render_template, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
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


@app.route('/user_page')
@login_required
def user_page():
    store_settings = get_store_settings()
    store_settings['title'] = 'Личный кабинет'
    db_sess = db_session.create_session()
    with open(f'accounts/user_{current_user.id}.json', 'r', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)['currencies']
    money = []
    for i in data.keys():
        logo = db_sess.query(Currency).filter(Currency.id == int(i)).first().logotype
        money.append(
            [url_for('static', filename=f'img/currencies/{logo}'), data[i]])
    return render_template('user_page.html', money=money, **store_settings)


@app.route('/get_bonus')
@login_required
def get_bonus():
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        jsonfile.seek(0)
        db_sess = db_session.create_session()
        for i in db_sess.query(Currency).all():
            money = random.randint(0, 9999)
            if i.is_integer == 0:
                money /= 10 ** random.randint(0, len(str(money)))
            data['currencies'][str(i.id)] += money
        json.dump(data, jsonfile)
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        user.got_bonus = 1
        current_user.got_bonus = 1
        db_sess.commit()
    return redirect(f'/user_page')


@app.route('/add_to_cart')
@login_required
def add_to_cart():
    info = dict()
    for i in ['item_id', 'currency_id', 'price', 'discount', 'discount_price']:
        info[i] = request.args.get(i)
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        data['shopping_cart']['items'].append(info)
        if info['currency_id'] not in data['shopping_cart']['summary'].keys():
            data['shopping_cart']['summary'][info['currency_id']] = 0
        if info['discount_price'] != 'None':
            data['shopping_cart']['summary'][info['currency_id']] += float(info['discount_price'])
        else:
            data['shopping_cart']['summary'][info['currency_id']] += float(info['price'])
        jsonfile.seek(0)
        json.dump(data, jsonfile)
    return redirect('/')


@app.route('/shopping_cart')
@login_required
def shoppping_cart(message=None):
    items = []
    summary = {}
    currencies = dict()
    db_sess = db_session.create_session()
    for i in db_sess.query(Currency).all():
        currencies[str(i.id)] = url_for('static', filename=f'img/currencies/{i.logotype}')
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        for i in data['shopping_cart']['items']:
            item = db_sess.query(Item).filter(Item.id == i['item_id']).first()
            items.append({'name': item.name, 'price': i['price'], 'discount': i['discount'],
                          'discount_price': i['discount_price'], 'currency': currencies[i['currency_id']],
                          'image': url_for('static', filename=f'img/items/{item.photo_name}'), 'id': i['item_id']})
        for i in data['shopping_cart']['summary'].keys():
            summary[i] = {'currency': currencies[i], 'price':  data['shopping_cart']['summary'][i]}
    store_settings = get_store_settings()
    store_settings['title'] = 'Корзина'
    return render_template('shopping_cart.html', items=items, summary=summary, message=message, **store_settings)


@app.route('/delete_from_cart/<int:item_id>')
@login_required
def delete_from_cart(item_id):
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        for i in range(len(data['shopping_cart']['items'])):
            if data['shopping_cart']['items'][i]['item_id'] == str(item_id):
                item = data['shopping_cart']['items'][i]
                del data['shopping_cart']['items'][i]
                if item['discount_price'] == 'None':
                    data['shopping_cart']['summary'][item['currency_id']] -= float(item['price'])
                else:
                    data['shopping_cart']['summary'][item['currency_id']] -= float(item['discount_price'])
                break
        jsonfile.seek(0)
        jsonfile.truncate()
        json.dump(data, jsonfile)
    return redirect('/shopping_cart')


if __name__ == '__main__':
    main()
