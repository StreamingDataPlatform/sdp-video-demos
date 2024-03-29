'''
Common Utilities
'''
import base64
import configparser
import json
import subprocess
import socket
import re
import time

class Config:
    def __init__(
        self,
        project,
        release_name,
        metrics_protocol,
        grafana_template,
        grafana_output,
        deploy_simulated_camera,
        deploy_recorder_pipeline,
        deploy_inference_pipeline,
        deploy_grafana_dashboard,
    ):
        self.project = project
        self.release_name = release_name
        self.metrics_protocol = metrics_protocol
        self.grafana_template = grafana_template
        self.grafana_output = grafana_output
        self.deploy_simulated_camera = deploy_simulated_camera
        self.deploy_recorder_pipeline = deploy_recorder_pipeline
        self.deploy_inference_pipeline = deploy_inference_pipeline
        self.deploy_grafana_dashboard = deploy_grafana_dashboard

    @classmethod
    def from_file(cls, file_path):
        config = configparser.ConfigParser()
        config.read(file_path)
        project = config["Project"]["project"]
        release_name = config["Project"]["release_name"]
        metrics_protocol = config["Metrics"]["protocol"]
        grafana_template = config["Metrics"]["grafana_template"]
        grafana_output = config["Metrics"]["grafana_output"]
        deploy_simulated_camera = config.getboolean("Components to deploy", "simulated_camera")
        deploy_recorder_pipeline = config.getboolean("Components to deploy", "recorder_pipeline")
        deploy_inference_pipeline = config.getboolean("Components to deploy", "inference_pipeline")
        deploy_grafana_dashboard = config.getboolean("Components to deploy", "grafana_dashboard")

        return cls(
            project,
            release_name,
            metrics_protocol,
            grafana_template,
            grafana_output,
            deploy_simulated_camera,
            deploy_recorder_pipeline,
            deploy_inference_pipeline,
            deploy_grafana_dashboard,
        )



def run_command(command, print_command=True):
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
    result = run_command(command, print_command=False)
    return result.stdout.strip() == expected_value


def get_k8s_ingress_host(ingress_name, namespace):
    command = f"kubectl get ingress {ingress_name} -n {namespace} -o jsonpath='{{.spec.rules[0].host}}'"
    result = run_command(command)
    return result.stdout.strip()


def get_k8s_service_local_address(service_name, namespace):
    command = f"kubectl get svc {service_name} -n {namespace} -o jsonpath='{{.spec.ports[0].port}}'"
    result = run_command(command)
    port = result.stdout.strip()
    host = f"{service_name}.{namespace}.svc.cluster.local"
    return host, port


def is_host_resolvable(hostname):
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.gaierror:
        return False


def wait_until_condition_met(condition_check, display_name, wait_time=5):
    print(f"Waiting {display_name}...", end="")
    while not condition_check():
        print(".", end="", flush=True)
        time.sleep(wait_time)
    print("")


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
