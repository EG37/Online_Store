from flask import Flask


app = Flask(__name__)
app.config['SECRET_KEY'] = 'store_secret_key'


def main():
    app.run(port=8080, host='127.0.0.1')


if __name__ == '__main__':
    main()
