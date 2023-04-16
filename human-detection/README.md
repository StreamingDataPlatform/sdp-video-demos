# Human Detection
Human detection inference demo on SDP

## Install
In SDP UI, create a new project with `Metrics` and `Video Server` features. Update the project name in `config.ini - [Project] - namespace` with newly created project name.

Install charts and set up Grafana using
```
$ ./install.sh
```
After finish install, setup camera and inference pipeline in SDP Project UI.
### Create Camera Secret
All camera connected through rtsp requires secret. Install script deployed two simulated cameras with secret `admin@password`.

Make sure secret `admin-secret` exists `Video - Camera Secrets`.

### Create Camera Recorder Pipeline
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


### Create GStreamer Pipelines
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


```