import argparse
import utils
import time
import json


def wait_until_host_resolvable(host):
    print(f"Waiting {host}...\n...", end="")
    while not utils.is_host_resolvable(host):
        print(".", end="", flush=True)
        time.sleep(5)
    print("")


def wait_until_project_ready(project):
    print(f"Waiting project {project}...\n...", end="")
    while not utils.is_k8s_resource_in_state("projects.nautilus.dellemc.com",
                                             project, project, "{.status.status}", "Ready"):
        print(".", end="", flush=True)
        time.sleep(5)
    print("")


def wait_until_camera_recorder_running(camera_recorder, namespace):
    print(f"Waiting camera recorder {camera_recorder}...\n...", end="")
    while not utils.is_k8s_resource_in_state("CameraRecorderPipeline",
                                             camera_recorder, namespace, "{.status.state}", "Running"):
        print(".", end="", flush=True)
        time.sleep(3)
    print("")


def create_grafana_datasource(protocol, grafana_uri, influxdb_uri, influxdb_database, influxdb_username, influxdb_password):
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
    result = utils.run_command(command)
    print(result.stdout)


def create_grafana_dashboard(protocol, grafana_uri, grafana_template, grafana_output, variable_map):
    # Generate dashboard from template
    utils.generate_file_from_template(
        grafana_template, grafana_output, variable_map)

    # Create dashboard
    command = (
        'curl -k '
        f'"{protocol}://admin:admin@{grafana_uri}/api/dashboards/db" '
        '-X POST '
        "-H 'Content-Type: application/json' "
        f"--data-binary @{grafana_output}"
    )
    result = utils.run_command(command)
    print(result.stdout)
    dashboard_url = f"{protocol}://{grafana_uri}"
    try:
        dashboard_suffix = json.loads(result.stdout)['url']
        if dashboard_suffix:
            return f"{dashboard_url}{dashboard_suffix}"
    except:
        return dashboard_url


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Read config file from --config argument")
    parser.add_argument('--config', type=str, required=True,
                        help="Path to the config file")
    args = parser.parse_args()
    config = utils.Config.from_file(args.config)

    print(f"[Install to Project {config.project}]\n")

    print("[Install SDP Project, Simulated Cameras, Metrics services]")
    # create namespace if not exists
    utils.run_command("kubectl get namespace |" +
                      f" grep -q \"^{config.project}\" ||" +
                      f" kubectl create namespace {config.project}")
    # install stage1
    utils.run_command("helm upgrade --install human-detection ./chart" +
                      f" -n {config.project}" +
                      " --set stageTags.stage1=true" + 
                      " --set stageTags.stage2=false")
    wait_until_project_ready(config.project)

    print("[Install Camera Recorder Pipelines]")
    utils.run_command("helm upgrade --install human-detection ./chart" +
                      f" -n {config.project}" +
                      " --set stageTags.stage1=true" + 
                      " --set stageTags.stage2=true")
    wait_until_camera_recorder_running("camera-recorder-1", config.project)
    wait_until_camera_recorder_running("camera-recorder-2", config.project)

    print("[TODO Install GStreamer Pipelines]")

    print("[Wait until Grafana/Video Server ready]")
    grafana_uri = utils.get_k8s_ingress_host(f"{config.release_name}-grafana",
                                         config.project)
    video_server_uri = utils.get_k8s_ingress_host(f"{config.release_name}-video-server",
                                              config.project)
    wait_until_host_resolvable(grafana_uri)
    wait_until_host_resolvable(video_server_uri)

    print("[Add Grafana data source]")
    influxdb_username, influxdb_password = utils.get_influxdb_creds('project-metrics-influxdb',
                                                                    config.project)
    influxdb_uri = utils.get_k8s_service_local_address("project-metrics",
                                                           config.project)
    create_grafana_datasource(config.metrics_protocol, grafana_uri, influxdb_uri,
                              "video_demo_db", influxdb_username, influxdb_password)

    print("[Create Grafana dashboard]")
    grafana_variable_map = {
        'video_server_uri': video_server_uri,
        'namespace': config.project,
        'protocol': config.metrics_protocol,
    }
    dashboard_url = create_grafana_dashboard(config.metrics_protocol, grafana_uri,
                                             config.grafana_template, config.grafana_output,
                                             grafana_variable_map)

    print("\nDone------------------------------------------------------------------")

    print("\nTo Access Grafana Dashboard:")
    print(
        f"1. Use {config.metrics_protocol}://{video_server_uri}/scopes to verify video server access")
    print(
        f"2. Access the dashboard at {dashboard_url}. Default username and password are both 'admin'")
