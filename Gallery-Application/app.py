from flask import Flask
app = Flask(__name__)

@app.route('/app/')
def hello_world():
   return 'Hello Worlds'

if __name__ == '__main__':
   app.run(port=5000, host="0.0.0.0")