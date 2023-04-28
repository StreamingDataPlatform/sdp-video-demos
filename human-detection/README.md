# Human Detection
Human detection inference demo on SDP

## Install
To ensure successful installation of the human detection inference demo, make sure following packages are installed:
```
python3
helm
kubectl
```

Please review settings in [`config.ini`](./config.ini). In most cases, the only change needed is to update the SDP project name in the project field. For more information on customizing the installation, refer to the [Customize Installation](#customize-installation) section.

To install the demo with your configs, run
```
$ bash ./install.sh
```

## Customized Installation
The installation can be customized by changing the configurations in the `config.ini` file. For example, if an existing RTSP camera is available, the user can set `simulated_camera = false` and configure the pipelines to use the address of the existing camera.

Instead of deploying the Camera Secrets, Camera Recorder Pipelines, and Gstreamer Pipelines through the script, the user may choose to do so in the SDP UI. These can be found under the `Analytics - <Project> - Video` panel in Dell Streaming Data Platform. The reference values used in the script can be found in the [helm charts](./chart/).

You may also refer to following sections for how to deploy the demo in UI,

### Reference: Camera Secret
For RTSP cameras, basic authentication is usually enabled. The installation script deploys a simulated RTSP camera with the username-password pair of `admin:password`. In SDP, the camera recorder pipeline reads the secret that stores the username and password for authentication.

### Reference: Camera Recorder Pipeline
| Field                  | Value                                                        |
| ---------------------- | ------------------------------------------------------------ |
| Host Address           | <release_name>-rtsp-simulator.\<namespace>.svc.cluster.local |
| Port                   | 8554                                                         |
| URL Path               | /cam1                                                        |
| Secret                 | admin-secret                                                 |
| Stream                 | camera1                                                      |
| Retention Policy Type  | days                                                         |
| Days                   | 3                                                            |
| Environment Properties | CAMERA_PROTOCOLS=tcp                                         |


### Reference: GStreamer Pipelines
| Field                    | Value                                                                         |
| ------------------------ | ----------------------------------------------------------------------------- |
| Name                     | human-detection-1                                                             |
| Image                    | devops-repo.isus.emc.com:8116/nautilus/video-demos/dlstreamer-pipeline:latest |
| Replicas                 | 1                                                                             |
| Pull Policy              | Always                                                                        |
| Liveness Probe           | False                                                                         |
| Environment Properties   | INPUT_STREAM=camera1                                                          |
| Environment Properties   | OUTPUT_VIDEO_STREAM=camera1-infer                                             |
| Environment Properties   | RECOVERY_TABLE=camera1-rec                                                    |
| Environment Properties   | ROI=[{"x":600,"y":180,"w":600,"h":500}]                                       |
| Environment Properties   | PRAVEGA_RETENTION_POLICY_TYPE=days                                            |
| Environment Properties   | PRAVEGA_RETENTION_DAYS=3                                                      |
| Environment Properties   | INFLUXDB_HOST=project-metrics.\<namespace>.svc.cluster.local                  |
| Environment Properties   | INFLUXDB_DEVICE=cam1                                                          |
| Environment Properties   | INFLUXDB_USERNAME=<influxdb_username>                                         |
| Environment Properties   | INFLUXDB_PASSWORD=<influxdb_password>                                         |
| Environment Properties   | INFLUXDB_DATABASE=foit                                                        |
| Environment Properties   | ENTRYPOINT=/opt/human-detection/human-detection.py                            |
| Resource Requests CPU    | 8                                                                             |
| Resource Requests Memory | 6G                                                                            |
| Resource Limits CPU      | 12                                                                            |
| Resource Limits Memory   | 10G                                                                           |

## Uninstall
To uninstall the demo as well as the SDP project demo is running on, run:
```
$ bash ./uninstall.sh
```
