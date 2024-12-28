from flask import Flask, Response

app = Flask(__name__)

@app.route('/')
def use_cpu():
    count = 1

    for i in range(1, 1000001):
        count = i

    print(f"count: {count}")
    return Response(str(count), mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)