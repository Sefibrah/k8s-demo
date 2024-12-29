from flask import Flask, Response

app = Flask(__name__)

@app.route('/')
def root_endpoint():
    count = 1

    for i in range(1, 1000001):
        count = i
    
    message = "Ibrahim Sefer - 220208812 - Cloud Tech Assignment #9" + "\n" + "Count: " + str(count)
    print(message)
    return Response(message, mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)