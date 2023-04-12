import subprocess
import base64
import json
from common import demo_namespace


def get_influxdb_creds():
    command = f'kubectl get secret project-metrics-influxdb -n {demo_namespace} -o json'
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    
    assert result.returncode == 0
    data = json.loads(result.stdout)
    username = base64.b64decode(data['data']['username']).decode('utf-8')
    password = base64.b64decode(data['data']['password']).decode('utf-8')
    return username, password


if __name__ == '__main__':
    username, password = get_influxdb_creds()
    print(f'influxdb-username: {username}')
    print(f'influxdb-password: {password}')
