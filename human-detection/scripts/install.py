import argparse
import utils
import json


def wait_until_host_resolvable(host):
    def condition_check(): return utils.is_host_resolvable(host)
    utils.wait_until_condition_met(condition_check, host)


def wait_until_project_ready(project):
    def condition_check(): return utils.is_k8s_resource_in_state("projects.nautilus.dellemc.com",
                                                                 project, project, "{.status.status}", "Ready")
    utils.wait_until_condition_met(condition_check, f"project {project}")


def wait_until_camera_recorder_running(camera_recorder, namespace):
    def condition_check(): return utils.is_k8s_resource_in_state("CameraRecorderPipeline",
                                                                 camera_recorder, namespace, "{.status.state}", "Running")
    utils.wait_until_condition_met(
        condition_check, f"camera recorder {camera_recorder}", wait_time=3)


def wait_until_gstreamer_pipeline_running(gstreamer_pipeline, namespace):
    def condition_check(): return utils.is_k8s_resource_in_state("GStreamerPipeline",
                                                                 gstreamer_pipeline, namespace, "{.status.state}", "Running")
    utils.wait_until_condition_met(
        condition_check, f"gstreamer pipeline {gstreamer_pipeline}", wait_time=3)


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
        description="Read config file from --config argument and install/uninstall using --uninstall flag")
    parser.add_argument('--config', type=str, required=True,
                        help="Path to the config file")
    parser.add_argument('--uninstall', action='store_true',
                        help="Use this flag to enable uninstall mode")
    args = parser.parse_args()
    config = utils.Config.from_file(args.config)

    if args.uninstall:
        print(f"[Uninstall from Project {config.project}]")
        utils.run_command(f"helm uninstall human-detection -n {config.project}")
        exit(0)

    print(f"[Install to Project {config.project}]")

    print("\n[Install SDP Project, Simulated Cameras, Metrics services]")
    # create namespace if not exists
    utils.run_command("kubectl get namespace |" +
                      f" grep -q \"^{config.project}\" ||" +
                      f" kubectl create namespace {config.project}")
    # install stage1
    utils.run_command("helm upgrade --install human-detection ./chart" +
                      f" -n {config.project}" +
                      " --set stageTags.stage1=true")
    wait_until_project_ready(config.project)
    # make sure video server is ready for playbacks in sdp
    wait_until_host_resolvable(
        utils.get_k8s_ingress_host("video", config.project))

    print("\n[Install Camera Recorder Pipelines]")
    utils.run_command("helm upgrade --install human-detection ./chart" +
                      f" -n {config.project}" +
                      " --set stageTags.stage1=true" +
                      " --set stageTags.stage2=true")
    wait_until_camera_recorder_running("camera-recorder-1", config.project)
    wait_until_camera_recorder_running("camera-recorder-2", config.project)

    print("\n[Install GStreamer Pipelines]")
    influxdb_host, ingress_port = utils.get_k8s_service_local_address("project-metrics",
                                                                      config.project)
    influxdb_username, influxdb_password = utils.get_influxdb_creds('project-metrics-influxdb',
                                                                    config.project)
    utils.run_command("helm upgrade --install human-detection ./chart" +
                      f" -n {config.project}" +
                      " --set stageTags.stage1=true" +
                      " --set stageTags.stage2=true" +
                      " --set stageTags.stage3=true" +
                      f" --set global.influxdb.host={influxdb_host}" +
                      f" --set global.influxdb.username={influxdb_username}" +
                      f" --set global.influxdb.password={influxdb_password}")
    wait_until_gstreamer_pipeline_running("human-detection-1", config.project)
    wait_until_gstreamer_pipeline_running("human-detection-2", config.project)

    print("\n[Add Grafana data source]")
    grafana_uri = utils.get_k8s_ingress_host(f"{config.release_name}-grafana",
                                             config.project)
    wait_until_host_resolvable(grafana_uri)
    influxdb_uri = f"{influxdb_host}:{ingress_port}"
    create_grafana_datasource(config.metrics_protocol, grafana_uri, influxdb_uri,
                              "video_demo_db", influxdb_username, influxdb_password)

    print("\n[Create Grafana dashboard]")
    video_server_uri = utils.get_k8s_ingress_host(f"{config.release_name}-video-server",
                                                  config.project)
    wait_until_host_resolvable(video_server_uri)
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
