from flask import Flask, url_for, redirect, render_template, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from data import db_session
from data.store import Store
from data.category import Category
from data.item import Item
from data.currency import Currency
from data.user import User
from forms.register_form import RegisterForm
from forms.login_form import LoginForm
from forms.search_form import SearchForm
import random
import json


# Запуск приложения через flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_store_secret_key'
# Создание менеджера логинов
login_manager = LoginManager()
login_manager.init_app(app)
# Подключение к базе данных
db_session.global_init("db/store_database.db")
# Создание магазина - заглушки
store = Store()


# Функция выбирает случайный магазин из базы данных
def set_current_store():
    global store
    session = db_session.create_session()
    stores = session.query(Store).all()
    store = random.choice(stores)


# Получение данных от текущего магазина
# Это нужно, чтобы легко менять название страниц
def get_store_settings():
    store_settings = dict()
    store_settings['title'] = store.name
    store_settings['slogan'] = store.slogan
    store_settings['logotype'] = url_for('static', filename=f'img/logotypes/{store.logotype}')
    store_settings['icon'] = url_for('static', filename=f'img/icons/{store.icon}')
    return store_settings


# Запуск сервера и выбор случайного магазина
def main():
    set_current_store()
    app.run(port=8080, host='127.0.0.1')


# Главная страница
@app.route('/')
def main_page():
    # Создание сессии
    session = db_session.create_session()
    # Получение данных текущего магазина
    store_settings = get_store_settings()
    categories = []
    items = session.query(Item).all()
    # Перестановка товаров в случайном порядке
    random.shuffle(items)
    # Выбор товара для особого предложения
    special_offer = items.pop()
    # Установка фото и описания для особого предложения
    special_offer.photo_name = url_for('static', filename=f'img/items/{special_offer.photo_name}')
    special_offer.description = special_offer.description.split(';')[0]
    # Создание словаря для товаров на главной странице
    items = {
        'items': items,
        'length': len(items) // 3
    }
    return render_template('main_page.html', special_offer=special_offer, items=items, **store_settings)


# Страница товара
@app.route('/item/<int:item_id>')
def item_page(item_id):
    store_settings = get_store_settings()
    session = db_session.create_session()
    # Получение товара по идентификатору
    item = session.query(Item).get(item_id)
    if not item:
        # Если товар не найден, возвращаю особую страницу
        store_settings['title'] = '?????????'
        return render_template('item_not_found.html', **store_settings)
    else:
        # Создание словаря с идентификатором, именем, фото и описанием
        item_info = dict()
        item_info['item_id'] = item_id
        item_info['name'] = item.name
        item_info['source'] = url_for('static', filename=f'img/items/{item.photo_name}')
        store_settings['title'] = item.name
        item_info['properties'] = item.description.split(';')
        # Если у товара есть особая цена и валюта, добавляю их в словарь
        if item.special_price:
            item_info['price'] = item.special_price
            currency = session.query(Currency).get(item.special_currency)
        # Если нет, выбираем случайные цену и валюту и заносим их в словарь
        else:
            item_info['price'] = random.randint(0, 99999999)
            item_info['price'] /= 10 ** random.randint(0, len(str(item_info['price'])))
            currency = random.choice(session.query(Currency).all())
        item_info['currency_id'] = currency.id
        # Загрузка фото для валюты
        item_info['currency'] = url_for('static', filename=f'img/currencies/'f'{currency.logotype}')
        # Если будет скидка, определяю её размер и новую цену
        if random.randint(1, 10) == 10:
            # Размер скидки в процентах
            item_info['discount'] = random.randint(1, 400)
            # Преобразование цены в зависимости от размера скидки
            item_info['discount_price'] = item_info['price'] - item_info['price'] * item_info['discount'] / 100
            if currency.is_integer:
                item_info['price'] = int(item_info['price'])
                item_info['discount_price'] = int(item_info['discount_price'])
        # Если нет, ставлю заглушку в словарь
        else:
            item_info['discount_price'] = None
            item_info['discount'] = None
        return render_template('item_page.html', **store_settings, **item_info)


# Страница регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Загрузка формы регистрации
    form = RegisterForm()
    store_settings = get_store_settings()
    store_settings['title'] = 'Регистрация'
    # Проверка правильности введённых данных
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
        # Создание нового пользователя и занесение в базу данных
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
        # Создание json-файла с данными нового пользователя: счёт, корзина и заказы
        with open(f'accounts/user_{user.id}.json', 'w', encoding='utf-8') as jsonfile:
            data = {'shopping_cart': {'items': [], 'summary': {}}, 'orders': {}, 'currencies': dict()}
            for i in db_sess.query(Currency).all():
                data['currencies'][i.id] = 0
            json.dump(data, jsonfile)
        return redirect("/")
    return render_template('register.html', form=form, **store_settings)


# Страница входа в аккаунт
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    store_settings = get_store_settings()
    store_settings['title'] = 'Вход'
    # Проверка данных
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        # Возврат страницы с сообщением в случае ошибки
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form, **store_settings)
    return render_template('login.html', form=form, **store_settings)


# Загрузка пользователя из базы данных
@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


# Функция для выхода из аккаунта
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


# Обновление страницы со сменой магазина
@app.route('/refresh')
def refresh():
    set_current_store()
    return redirect('/')


# Личный кабинет пользователя
@app.route('/user_page')
@login_required
def user_page():
    store_settings = get_store_settings()
    store_settings['title'] = 'Личный кабинет'
    db_sess = db_session.create_session()
    # Загрузка данных о счёте из json-файла пользователя
    with open(f'accounts/user_{current_user.id}.json', 'r', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)['currencies']
    money = []
    # Загрузка фотографий валют
    for i in data.keys():
        logo = db_sess.query(Currency).filter(Currency.id == int(i)).first().logotype
        money.append(
            [url_for('static', filename=f'img/currencies/{logo}'), data[i]])
    return render_template('user_page.html', money=money, **store_settings)


# Получение бонуса пользователем
@app.route('/get_bonus')
@login_required
def get_bonus():
    # Загрузка данных пользователя из json-файла
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        jsonfile.seek(0)
        db_sess = db_session.create_session()
        # Добавление случайного количества каждой валюты
        for i in db_sess.query(Currency).all():
            money = random.randint(0, 9999)
            money /= 10 ** random.randint(0, len(str(money)))
            if i.is_integer == 1:
                money = int(money)
            data['currencies'][str(i.id)] += money
        # Запись в json-файл новых данных
        json.dump(data, jsonfile)
        # Смена значения логического флага got_bonus для текущего пользователя и записи в базе данных
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        user.got_bonus = 1
        current_user.got_bonus = 1
        db_sess.commit()
    return redirect(f'/user_page')


# Добавление товара в корзину
@app.route('/add_to_cart')
@login_required
def add_to_cart():
    info = dict()
    # Получение информации из запроса
    for i in ['item_id', 'currency_id', 'price', 'discount', 'discount_price']:
        info[i] = request.args.get(i)
    # Загрузка данных из файла пользователя
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        # Добавление информации о товаре
        data['shopping_cart']['items'].append(info)
        # Добавление цены товара к сумме цен товаров в корзине
        if info['currency_id'] not in data['shopping_cart']['summary'].keys():
            data['shopping_cart']['summary'][info['currency_id']] = 0
        if info['discount_price'] != 'None':
            data['shopping_cart']['summary'][info['currency_id']] += float(info['discount_price'])
        else:
            data['shopping_cart']['summary'][info['currency_id']] += float(info['price'])
        # Перезапись данных
        jsonfile.seek(0)
        json.dump(data, jsonfile)
    return redirect('/')


# Страница корзины
@app.route('/shopping_cart')
@login_required
def shopping_cart(message=None):
    items = []
    summary = {}
    currencies = dict()
    db_sess = db_session.create_session()
    # Создание словаря с фотографиями валюты
    for i in db_sess.query(Currency).all():
        currencies[str(i.id)] = url_for('static', filename=f'img/currencies/{i.logotype}')
    # Загрузка данных из файла
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        # Заполенение списка с информацией о товарах
        for i in data['shopping_cart']['items']:
            item = db_sess.query(Item).filter(Item.id == i['item_id']).first()
            items.append({'name': item.name, 'price': i['price'], 'discount': i['discount'],
                          'discount_price': i['discount_price'], 'currency': currencies[i['currency_id']],
                          'image': url_for('static', filename=f'img/items/{item.photo_name}'), 'id': i['item_id']})
        # Заполнение словаря с суммой цен товаров в корзине
        for i in data['shopping_cart']['summary'].keys():
            summary[i] = {'currency': currencies[i], 'price':  data['shopping_cart']['summary'][i]}
    store_settings = get_store_settings()
    store_settings['title'] = 'Корзина'
    return render_template('shopping_cart.html', items=items, summary=summary, message=message, **store_settings)


# Удаление товара из корзины
@app.route('/delete_from_cart/<int:item_id>')
@login_required
def delete_from_cart(item_id):
    # Загрузка данных
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        for i in range(len(data['shopping_cart']['items'])):
            # Удаление записи о товаре
            if data['shopping_cart']['items'][i]['item_id'] == str(item_id):
                item = data['shopping_cart']['items'][i]
                del data['shopping_cart']['items'][i]
                # Вычет цены из суммы цен товаров
                if item['discount_price'] == 'None':
                    data['shopping_cart']['summary'][item['currency_id']] -= float(item['price'])
                else:
                    data['shopping_cart']['summary'][item['currency_id']] -= float(item['discount_price'])
                break
        # Перезапись данных
        jsonfile.seek(0)
        jsonfile.truncate()
        json.dump(data, jsonfile)
    return redirect('/shopping_cart')


# Страница поиска
@app.route('/search', methods=['GET', 'POST'])
def search_page():
    # Загрузка формы
    form = SearchForm()
    db_sess = db_session.create_session()
    # Занесение категорий в форму
    form.category.choices = ['Всё']
    form.category.choices.extend([i.name for i in db_sess.query(Category).all()])
    store_settings = get_store_settings()
    store_settings['title'] = 'Поиск'
    # Обработка поиска
    if form.validate_on_submit():
        # Поиск только по имени
        if form.category.data != 'Всё':
            category_id = db_sess.query(Category).filter(Category.name == form.category.data).first().id
            items = db_sess.query(Item).filter(Item.name.like(f"%{form.name.data}%"), Item.category == category_id).all()
        # Поиск по имени и категории
        else:
            items = db_sess.query(Item).filter(Item.name.like(f"%{form.name.data}%")).all()
        # Заполенение словаря получеными данными
        items = {'items': items, 'rows': len(items) // 3 if len(items) % 3 == 0 else len(items) // 3 + 1,
                 'length': len(items)}
        # Возврат результатов
        return render_template('search.html', items=items, form=form, **store_settings)
    return render_template('search.html', items={'items': []}, form=form, **store_settings)


# Оформление заказа
@app.route('/order')
@login_required
def order():
    # Логический флаг для идентификации успеха заказа
    success = True
    # Загрузка данных пользователя
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        # Перебор значений валют в сумме цен товаров в корзине
        # Если какой-то валюты не хватает, меняю значение флага на False
        for i in data['shopping_cart']['summary'].keys():
            if data['currencies'][i] < data['shopping_cart']['summary'][i]:
                success = False
                break
        # В случае нехватки средств возвращаю страницу корзины с соответствувющим сообщением
        if not success:
            return shopping_cart('На вашем счёте недостаточно средств для оформления заказа')
        else:
            # В противном случае генерирую идентификатор заказа
            while True:
                key = random.randint(100000, 999999)
                if key not in data['orders'].keys():
                    break
            # Заношу данные о заказе в данные опльзователя
            data['orders'][key] = dict()
            data['orders'][key]['summary'] = data['shopping_cart']['summary'].copy()
            # Вычитаю сумму цен заказа
            for i in list(data['shopping_cart']['summary']):
                data['currencies'][i] -= data['shopping_cart']['summary'][i]
                del data['shopping_cart']['summary'][i]
            data['orders'][key]['items'] = data['shopping_cart']['items']
            data['shopping_cart']['items'] = []
            # Перезаписываю данные в файл
            jsonfile.seek(0)
            jsonfile.truncate()
            json.dump(data, jsonfile)
            return redirect('/orders')


# Страница заказов
@app.route('/orders')
@login_required
def orders():
    store_settings = get_store_settings()
    store_settings['title'] = 'Заказы'
    # Загрузка данных пользователя
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
    return render_template('orders.html', orders=data['orders'], **store_settings)


# Удаление заказа
@app.route('/delete_order/<int:order_id>')
@login_required
def delete_order(order_id):
    order_id = str(order_id)
    # Загрузка данных
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        # Проверка на наличие заказа в данных по идентификатору
        if order_id in data['orders'].keys():
            # Удаление заказа и перезпись
            del data['orders'][order_id]
            jsonfile.seek(0)
            jsonfile.truncate()
            json.dump(data, jsonfile)
            return redirect('/orders')
        else:
            return abort(404)


# Страница заказа
@app.route('/order/<int:order_id>')
@login_required
def order_page(order_id):
    store_settings = get_store_settings()
    order_id = str(order_id)
    store_settings['title'] = 'Заказ №' + order_id
    # Загрузка данных
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        if order_id not in data['orders'].keys():
            return abort(404)
    order_data = {'items': [], 'summary': {}}
    db_sess = db_session.create_session()
    currencies = dict()
    # Создание словаря с фото валют
    for i in db_sess.query(Currency).all():
        currencies[str(i.id)] = url_for('static', filename=f'img/currencies/{i.logotype}')
    # Заполнение списка товаров в заказе
    for i in data['orders'][order_id]['items']:
        item = db_sess.query(Item).filter(Item.id == int(i['item_id'])).first()
        order_data['items'].append({'name': item.name, 'price': i['price'], 'discount': i['discount'],
                          'discount_price': i['discount_price'], 'currency': currencies[i['currency_id']],
                          'image': url_for('static', filename=f'img/items/{item.photo_name}'), 'id': i['item_id']})
    # Заполенение словаря с суммой
    for i in data['orders'][order_id]['summary'].keys():
        order_data['summary'][i] = {'currency': currencies[i], 'price':  data['orders'][order_id]['summary'][i]}
    return render_template('order.html', order_data=order_data, order_id=order_id, **store_settings)


# Возвращение денег за заказ
@app.route('/refund_order/<int:order_id>')
@login_required
def refund_order(order_id):
    order_id = str(order_id)
    # Загрузка данных
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        # Поиск заказа по идентификатору
        if order_id not in data['orders'].keys():
            return abort(404)
        # Возврат денег
        for i in data['orders'][order_id]['summary'].keys():
            data['currencies'][i] += data['orders'][order_id]['summary'][i]
        # Перезапись данных
        jsonfile.seek(0)
        jsonfile.truncate()
        json.dump(data, jsonfile)
    # Редирект на страницу удаления заказа
    return delete_order(order_id)


# Страница обмена валют
@app.route('/exchange')
@login_required
def exchange(message=None):
    store_settings = get_store_settings()
    store_settings['title'] = 'Обмен валют'
    db_sess = db_session.create_session()
    data = []
    currencies = db_sess.query(Currency).all()
    # Случайное определение валюты и цены
    for i in currencies:
        j = random.choice(currencies)
        price = random.randint(0, 9999)
        price /= 10 ** random.randint(0, len(str(price)))
        if j.is_integer == 1:
            price = int(price)
        # Занесение курса в список
        data.append({'first_id': i.id, 'first_logo': url_for('static', filename=f'img/currencies/{i.logotype}'),
                     'second_id': j.id, 'second_logo': url_for('static', filename=f'img/currencies/{j.logotype}'),
                     'amount': price})
    return render_template('exchange.html', message=message, data=data, **store_settings)


# Обработка обмена валют
@app.route('/change_currencies')
@login_required
def change_currencies():
    info = dict()
    # Получение данных из запроса
    for i in ['first_id', 'second_id', 'amount']:
        info[i] = request.args.get(i)
    # Загрузка данных пользователя
    with open(f'accounts/user_{current_user.id}.json', 'r+', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        # Проверка наличия достаточного количества денег у пользователя
        if data['currencies'][info['first_id']] < 1:
            return exchange('На вашем счёте недостаточно средств для совершения обмена')
        else:
            # Совершение обмена
            data['currencies'][info['first_id']] -= 1
            data['currencies'][info['second_id']] += float(info['amount'])
            # Перезапись данных
            jsonfile.seek(0)
            jsonfile.truncate()
            json.dump(data, jsonfile)
            return redirect('/exchange')


# Замена стандартных страниц ошибок
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html')


@app.errorhandler(401)
def unauthorized(error):
    return render_template('401.html')


@app.errorhandler(500)
def server_error(error):
    return render_template('500.html')


if __name__ == '__main__':
    main()
