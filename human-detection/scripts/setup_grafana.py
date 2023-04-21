import argparse
import base64
import configparser
import re
import json
import time
import subprocess
import socket


def get_influxdb_creds(namespace):
    command = f'kubectl get secret project-metrics-influxdb -n {namespace} -o json'
    result = subprocess.run(
        command, capture_output=True, text=True, shell=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    username = base64.b64decode(data['data']['username']).decode('utf-8')
    password = base64.b64decode(data['data']['password']).decode('utf-8')
    return username, password


def get_ingress_host(ingress_name, namespace):
    command = f"kubectl get ingress {ingress_name} -n {namespace} -o jsonpath='{{.spec.rules[0].host}}'"
    result = subprocess.run(
        command, capture_output=True, text=True, shell=True)
    assert result.returncode == 0
    return result.stdout.strip()


def get_service_cluster_local_address(service_name, namespace):
    command = f"kubectl get svc {service_name} -n {namespace} -o jsonpath='{{.spec.ports[0].port}}'"
    result = subprocess.run(
        command, capture_output=True, text=True, shell=True)
    assert result.returncode == 0
    port = result.stdout.strip()
    local_address = f"{service_name}.{namespace}.svc.cluster.local:{port}"
    return local_address


def create_datasource(protocol, grafana_uri, influxdb_uri, influxdb_database, influxdb_username, influxdb_password):
    command = (
        'curl -k '
        f'"{protocol}://admin:admin@{grafana_uri}/api/datasources" '
        '-X POST '
        "-H 'Content-Type: application/json;charset=UTF-8' "
        f"--data-binary '{{"
        f"\"name\":\"InfluxDB\","
        f"\"type\":\"influxdb\","
        f"\"url\":\"http://{influxdb_uri}\","
        f"\"access\":\"proxy\","
        f"\"isDefault\":true,"
        f"\"database\":\"{influxdb_database}\","
        f"\"user\":\"{influxdb_username}\","
        f"\"password\":\"{influxdb_password}\""
        f"}}' "
    )
    result = subprocess.run(
        command, capture_output=True, text=True, shell=True)
    assert result.returncode == 0
    print(result.stdout)


def create_dashboard(protocol, grafana_uri, grafana_template, grafana_output, variable_map):
    # Generate dashboard from template
    pattern = re.compile(r'%\{(.+?)\}%')
    with open(grafana_template, 'r') as infile, open(grafana_output, 'w') as outfile:
        for line in infile:
            modified_line = line
            for match in pattern.finditer(line):
                placeholder = match.group(1)
                assert placeholder in variable_map
                modified_line = modified_line.replace(
                    f'%{{{placeholder}}}%', str(variable_map[placeholder]))
            outfile.write(modified_line)

    # Create dashboard
    command = (
        'curl -k '
        f'"{protocol}://admin:admin@{grafana_uri}/api/dashboards/db" '
        '-X POST '
        "-H 'Content-Type: application/json' "
        f"--data-binary @{grafana_output}"
    )
    result = subprocess.run(
        command, capture_output=True, text=True, shell=True)
    assert result.returncode == 0
    print(result.stdout)
    try:
        return json.loads(result.stdout)['url']
    except:
        return None


def is_host_resolvable(hostname):
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.gaierror:
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Read config file from --config argument")
    parser.add_argument('--config', type=str, required=True,
                        help="Path to the config file")
    args = parser.parse_args()

    # Read config
    config = configparser.ConfigParser()
    config.read(args.config)
    project_namespace = config['Project']['namespace']
    project_release_name = config['Project']['release_name']
    metrics_protocol = config['Metrics']['protocol']
    influxdb_database = config['Metrics']['influxdb_database']
    grafana_template = config['Metrics']['grafana_template']
    grafana_output = config['Metrics']['grafana_output']

    print("[Validate URIs]")
    influxdb_username, influxdb_password = get_influxdb_creds(
        project_namespace)
    grafana_uri = get_ingress_host(
        f"{project_release_name}-grafana", project_namespace)
    influxdb_uri = get_service_cluster_local_address(
        "project-metrics", project_namespace)
    video_server_uri = get_ingress_host(
        f"{project_release_name}-video-server", project_namespace)
    print(f"grafana_uri: {grafana_uri}")
    print(f"video_server_uri: {video_server_uri}")

    print(f"[Wait until Grafana/Video Server accessible]")
    print("Waiting Grafana...", end="")
    while not is_host_resolvable(grafana_uri):
        print(".", end="", flush=True)
        time.sleep(5)
    print("\nWaiting Video Server...", end="")
    while not is_host_resolvable(video_server_uri):
        print(".", end="", flush=True)
        time.sleep(5)
    print("")

    print("[Add data source]")
    create_datasource(metrics_protocol, grafana_uri, influxdb_uri,
                      influxdb_database, influxdb_username, influxdb_password)

    print("[Create dashboard]")
    grafana_variable_map = {
        'video_server_uri': video_server_uri,
        'namespace': project_namespace,
        'protocol': metrics_protocol,
    }
    dashboard_suffix = create_dashboard(
        metrics_protocol, grafana_uri, grafana_template, grafana_output, grafana_variable_map)
    # Compose full dashboard url
    dashboard_url = f"{metrics_protocol}://{grafana_uri}"
    if dashboard_suffix:
        dashboard_url = f"{dashboard_url}{dashboard_suffix}"


    print("\nDone------------------------------------------------------------------")

    print("\n[Values for deployement in UI]")
    print(f"Simulated Camera Address: {project_release_name}-rtsp-simulator.{project_namespace}.svc.cluster.local")
    print(f"InfluxDB Host: project-metrics.{project_namespace}.svc.cluster.local")
    print(f"InfluxDB Username: {influxdb_username}")
    print(f"InfluxDB Password: {influxdb_password}")
    print("\n[Access Grafana Dashboard]")
    print(f"1. Use {metrics_protocol}://{video_server_uri}/scopes to verify video server access")
    print(f"2. Access the dashboard at {dashboard_url}. Default username and password are both 'admin'")
