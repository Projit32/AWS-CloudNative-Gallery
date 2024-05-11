from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/app/')
def hello_world():
   return 'Hello Worlds'

@app.route('/healthCheck/', methods=['GET'])
def health_check():
   return jsonify({"Status":"UP"})

if __name__ == '__main__':
   app.run(port=5000, host="0.0.0.0")