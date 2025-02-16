from flask import Flask, jsonify
import os
app = Flask(__name__)

@app.route('/app/')
def hello_world():
   return 'Hello Worlds'

@app.route('/healthCheck/', methods=['GET'])
def health_check():
   return jsonify({"Status":"UP"})

if __name__ == '__main__':
   print(os.getenv("PORT"))
   app.run(port=os.getenv("PORT"), host="0.0.0.0")