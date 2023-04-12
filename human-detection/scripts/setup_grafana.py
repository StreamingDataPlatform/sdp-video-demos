import re
import os
import json
import common
from get_influxdb_creds import get_influxdb_creds
import subprocess

def get_ingress_host(ingress_name, namespace):
    command = f"kubectl get ingress {ingress_name} -n {namespace} -o jsonpath='{{.spec.rules[0].host}}'"

    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    assert result.returncode == 0
    return result.stdout.strip()


def get_service_cluster_local_address(service_name, namespace):
    command = f"kubectl get svc {service_name} -n {namespace} -o jsonpath='{{.spec.ports[0].port}}'"

    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    assert result.returncode == 0
    port = result.stdout.strip()
    local_address = f"{service_name}.{namespace}.svc.cluster.local:{port}"
    return local_address


def create_datasource(protocol, grafana_uri, influxdb_uri, influxdb_username, influxdb_password):
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
            f"\"database\":\"{common.influxdb_database}\","
            f"\"user\":\"{influxdb_username}\","
            f"\"password\":\"{influxdb_password}\""
        f"}}' "
    )

    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    assert result.returncode == 0
    print(result.stdout)


def generate_dashboard_data(variable_map):
    pattern = re.compile(r'%\{(.+?)\}%')
    with open(common.grafana_dashboard_template, 'r') as infile, open(common.grafana_dashboard, 'w') as outfile:
        for line in infile:
            modified_line = line
            for match in pattern.finditer(line):
                placeholder = match.group(1)
                assert placeholder in variable_map
                modified_line = modified_line.replace(f'%{{{placeholder}}}%', str(variable_map[placeholder]))
            outfile.write(modified_line)
    return common.grafana_dashboard


def create_dashboard(protocol, grafana_uri, variable_map):
    dashboard_data = generate_dashboard_data(variable_map)
    command = (
        'curl -k '
        f'"{protocol}://admin:admin@{grafana_uri}/api/dashboards/db" '
        '-X POST '
        "-H 'Content-Type: application/json' "
        f"--data-binary @{dashboard_data}"
    )

    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    assert result.returncode == 0
    print(result.stdout)
    try:
        dashboard_url = json.loads(result.stdout)['url']
        return dashboard_url
    except:
        return None

if __name__=='__main__':
    # Change the current working directory to the directory of this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("Setting up URIs...")

    influxdb_username, influxdb_password = get_influxdb_creds()
    print(f"influxdb_username: {influxdb_username}")
    print(f"influxdb_password: {influxdb_password}")
    grafana_uri = get_ingress_host(f"{common.demo_release_name}-grafana", common.demo_namespace)
    print(f"grafana_uri: {grafana_uri}")
    influxdb_uri = get_service_cluster_local_address("project-metrics", common.demo_namespace)
    print(f"influxdb_uri: {influxdb_uri}")
    video_server_uri = get_ingress_host(f"{common.demo_release_name}-video-server", common.demo_namespace)
    print(f"video_server_uri: {video_server_uri}")
    
    print("\nAdd data source...")
    create_datasource(common.protocol, grafana_uri, influxdb_uri, influxdb_username, influxdb_password)

    print("\nCreate dashboard...")
    grafana_variable_map = {
        'video_server_uri': video_server_uri,
        'namespace': common.demo_namespace,
        'protocol': common.protocol,
    }
    dashboard_suffix = create_dashboard(common.protocol, grafana_uri, grafana_variable_map)
    # get full dashboard url
    dashboard_url = f"{common.protocol}://{grafana_uri}"
    if dashboard_suffix:
        dashboard_url = f"{dashboard_url}/{dashboard_suffix}"    

    print("\nDone!")
    print(f"\nYou can now access the dashboard at {dashboard_url}")
    print(f"Use {common.protocol}://{video_server_uri}/scopes to verify video server access") 
    print("The default username and password are both 'admin'")
