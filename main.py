from flask import Flask
from data import db_session
from data.store import Store


app = Flask(__name__)
db_session.global_init("db/store_database.db")
store = Store()


def main():
    app.run(port=8080, host='127.0.0.1')


if __name__ == '__main__':
    main()
