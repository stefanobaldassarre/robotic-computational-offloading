import time
import requests
from flask import Flask, request, jsonify
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

@app.post('/process')
def process():
    service_start = time.perf_counter()
    raw = request.get_data()
    start = time.perf_counter()
    try:
        response = requests.post('http://192.168.50.30:5301/process', data=raw,
                                 headers={'Content-Type':'audio/wav'}, timeout=(5, 60))
        response.raise_for_status()
        # End after complete response body; before parsing remote JSON.
        offload_ms = (time.perf_counter() - start) * 1000
        result = response.json()
        result['remote_processing_time_ms'] = result.pop('processing_time_ms')
        result['remote_service_time_ms'] = result.pop('service_time_ms')
        result['offload_e2e_time_ms'] = offload_ms
        result['proxy_service_time_ms'] = (time.perf_counter() - service_start) * 1000
        return jsonify(result)
    except (requests.RequestException, ValueError, KeyError) as exc:
        return jsonify(error=str(exc)), 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5302, threaded=False)
