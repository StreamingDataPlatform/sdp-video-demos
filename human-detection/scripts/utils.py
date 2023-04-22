'''
Common Utilities
'''
import base64
import configparser
import json
import subprocess
import socket
import re


class Config:
    def __init__(self, project, release_name, metrics_protocol, grafana_template, grafana_output):
        self.project = project
        self.release_name = release_name
        self.metrics_protocol = metrics_protocol
        self.grafana_template = grafana_template
        self.grafana_output = grafana_output

    @classmethod
    def from_file(cls, file_path):
        config = configparser.ConfigParser()
        config.read(file_path)
        project = config['Project']['project']
        release_name = config['Project']['release_name']
        metrics_protocol = config['Metrics']['protocol']
        grafana_template = config['Metrics']['grafana_template']
        grafana_output = config['Metrics']['grafana_output']

        return cls(
            project,
            release_name,
            metrics_protocol,
            grafana_template,
            grafana_output
        )


def run_command(command, print_command=False):
    if print_command:
        print(f"$ {command}")
    result = subprocess.run(
        command, capture_output=True, text=True, shell=True)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    return result


def get_influxdb_creds(influxdb_name, namespace):
    command = f'kubectl get secret {influxdb_name} -n {namespace} -o json'
    result = run_command(command)
    data = json.loads(result.stdout)
    username = base64.b64decode(data['data']['username']).decode('utf-8')
    password = base64.b64decode(data['data']['password']).decode('utf-8')
    return username, password


def is_k8s_resource_in_state(resource, resource_name, namespace, state_jsonpath, expected_value):
    command = f"kubectl get {resource} {resource_name} -n {namespace} -o jsonpath='{state_jsonpath}\n'"
    result = run_command(command)
    return result.stdout.strip() == expected_value


def get_k8s_ingress_host(ingress_name, namespace):
    command = f"kubectl get ingress {ingress_name} -n {namespace} -o jsonpath='{{.spec.rules[0].host}}'"
    result = run_command(command)
    return result.stdout.strip()


def get_k8s_service_local_address(service_name, namespace):
    command = f"kubectl get svc {service_name} -n {namespace} -o jsonpath='{{.spec.ports[0].port}}'"
    result = run_command(command)
    port = result.stdout.strip()
    local_address = f"{service_name}.{namespace}.svc.cluster.local:{port}"
    return local_address


def is_host_resolvable(hostname):
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.gaierror:
        return False


def generate_file_from_template(template_file, output_file, variable_map):
    pattern = re.compile(r'%\{(.+?)\}%')
    with open(template_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            modified_line = line
            for match in pattern.finditer(line):
                placeholder = match.group(1)
                assert placeholder in variable_map
                modified_line = modified_line.replace(
                    f'%{{{placeholder}}}%', str(variable_map[placeholder]))
            outfile.write(modified_line)
