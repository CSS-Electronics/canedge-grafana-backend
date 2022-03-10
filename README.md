# CANedge Grafana Backend - Visualize CAN/LIN Data in Dashboards

This project enables easy dashboard visualization of log files from the [CANedge](https://www.csselectronics.com/pages/can-bus-hardware-products) CAN/LIN data logger. 

Specifically, a light-weight backend app loads, DBC decodes and parses MDF log files from local disk or an S3 server. This is done 'on demand' in response to query requests sent from a [Grafana dashboard](https://grafana.com/) frontend by end users. 

**This project is currently in BETA - major changes will be made.**

![CAN Bus Grafana Dashboard](https://canlogger1000.csselectronics.com/img/can-bus-telematics-dashboard-template.png)


## Backend vs. Writer
We provide two options for integrating your CANedge data with Grafana dashboards:

The backend app only processes data 'when needed' by an end user - and requires no database. It is ideal when you have large amounts of data - as you only process the data you need to visualize.

In contrast, the [Dashboard Writer](https://github.com/CSS-Electronics/dashboard-writer) integration requires that you process relevant data in advance (e.g. periodically or on-file-upload) and write the decoded data to a database (e.g. InfluxDB). It is ideal if the dashboard loading speed is critical - but with the downside that large amounts of data is processed & stored (at a cost) without being used.

-----

## Features

```
- allow users to visualize data from all of your devices & log files in Grafana 
- data is only processed "on request" - avoiding the need for costly databases
- data can be fetched from local disk or S3
- data can be visualized as soon as log files are uploaded to S3 for 'near real-time updates'
- the backend app can be easily deployed on e.g. your PC or AWS EC2 instance 
- plug & play dashboard templates & sample data let you get started quickly 
- view log file sessions & splits via Annotations, enabling easy identification of underlying data 
- allow end users control over what devices/signals are displayed via flexible Variables
```

----

## Installation
In this section we detail how to deploy the app on a PC or an AWS EC2 instance. 

- Note: Follow the guide using our `LOG/` sample data before using your own data
- Note: We use port `8080` for illustration (another port can be used)



### 1: Set up Grafana Cloud
- [Set up](https://grafana.com/auth/sign-up/create-user) a free Grafana Cloud account and log in
- In `Configuration/Plugins` install `SimpleJSON` and `TrackMap`, then login again 
- In `Configuration/DataSources` select `Add datasource` and `SimpleJSON`
- Enter a dummy URL for now, `http://5.105.117.49:8080/`, hit `Save & test` and verify that it fails 
- In `Dashboards/Browse` click `Import`, then load the `dashboard-template.json` from this repo 

Your dashboard is now ready once you replace the 'dummy URL' with a valid endpoint.

<img src="https://canlogger1000.csselectronics.com/img/Grafana-SimpleJSON-datasource.jpg" width="679.455" height="226.477">

 
### 2: Deploy the backend app 
Below we explain how to set up the backend app on your PC or an [AWS EC2](https://aws.amazon.com/ec2/) instance.

#### Example A: Deploy the backend app on your PC 
A local PC deployment is ideal for testing, as well as parsing data from local disk or MinIO S3:

- Install Python 3.7 for Windows ([32 bit](https://www.python.org/ftp/python/3.7.9/python-3.7.9.exe)/[64 bit](https://www.python.org/ftp/python/3.7.9/python-3.7.9-amd64.exe)) or [Linux](https://www.python.org/downloads/release/python-379/) (_enable 'Add to PATH'_)
- Open your [command prompt](https://www.youtube.com/watch?v=bgSSJQolR0E&t=47s) and enter below:
```
git clone https://github.com/CSS-Electronics/canedge-grafana-backend.git
cd canedge-grafana-backend
pip install -r requirements.txt
python canedge_datasource_cli.py file:///%cd%/LOG --port 8080
```
- Verify that you see an `OK` when opening `http://localhost:8080` in your browser

##### Set up port forwarding for access via the internet

- Set up [port forwarding](https://portforward.com/) on your WiFi router for port `8080`
- Run the app again (you may need to allow access via your firewall)
- Find your [public IP](https://www.whatismyip.com/) to get your endpoint as: `http://IP:port` (e.g. `http://5.105.117.49:8080/`)
- Verify that you see an `OK` when opening the endpoint in your browser
- In Grafana, update your dummy URL with the endpoint and click `Save & test`
- Verify that your datasource is OK and that your imported panel displays the sample data


#### Example B: Deploy the backend app on AWS EC2
An AWS EC2 instance is ideal for parsing data from AWS S3:

- Login to AWS, search for `EC2/Instances` and click `Launch instances`
- Select `Ubuntu Server 20.04 LTS (HVM), SSD Volume Type`, `t3.small` and proceed
- In `Step 6`, click `Add Rule/Custom TCP Rule` and set `Port Range` to `8080`
- Launch the instance, then create & store your credentials (we will not use them for now) 
- Wait a few minutes, then enter your instance and note your `Public IPv4 address`
- Click `Connect/Connect` to enter the GUI console, then enter the following:

```
sudo apt update
sudo apt install python3 python3-pip tmux
git clone https://github.com/CSS-Electronics/canedge-grafana-backend.git
cd canedge-grafana-backend
pip install -r requirements.txt
tmux
python3 canedge_datasource_cli.py file:///$PWD/LOG --port 8080

```

- Verify that you see an `OK` when opening the endpoint (`http://IP:port`) in your browser
- In Grafana, update your JSON URL with the endpoint and click `Save & test`
- Verify that your datasource is OK and that your imported dashboard panel displays your data
- In the GUI console, press `Ctrl B` then `D` to de-attach from the session

##### Managing your EC2

Below commands are useful in managing your `tmux` session:

- `tmux`: Start session
- `tmux ls`: List sessions 
- `tmux attach`: Re-attach to session
- `tmux kill-session`: Stop session

For production deployments you may want to deploy a service that e.g. auto-reboots if killed. 

##### Regarding EC2/S3 costs
You can find details on AWS EC2 pricing [here](https://aws.amazon.com/ec2/pricing/on-demand/). A t3.small instance typically costs ~0.02$/hour (~15-20$/month). We recommend that you monitor usage during your tests early on to ensure that no unexpected cost developments occur. Note also that you do not pay for the data transfer from S3 into EC2 if deployed within the same region. 


-----

### 3: Modify your deployment

### Parse data from S3

The above examples parse data from local disk. If you wish to parse data from an S3 server (MinIO, AWS, ...), you can use below syntax to start the backend (use `python3` on EC2):

```
python canedge_datasource_cli.py [endpoint] --port 8080 --s3_ak [access_key] --s3_sk [secret_key] --s3_bucket [bucket]
```

- AWS S3 endpoint example: `https://s3.eu-central-1.amazonaws.com`
- MinIO S3 endpoint example: `http://192.168.192.1:9000`

### Add DBC files 
All DBC files placed in the root of the parsed folder will be loaded and available for decoding (see the `LOG/` folder example). If you need to use multiple DBC files, consider merging & trimming these for performance. 


### Customize your Grafana dashboard

The `dashboard-template.json` can be used to identify how to make queries, incl. below examples:

```
# create a fully customized query that depends on what the user selects in the dropdown 
{"device":"${DEVICE}","itf":"${ITF}","chn":"${CHN}","db":"${DB}","signal":"${SIGNAL}"}

# create a query for a panel that locks a signal, but keeps the device selectable
{"device":"${DEVICE}","itf":"CAN","chn":"CH2","db":"canmod-gps","signal":"Speed"}

# create a query for parsing multiple signals, e.g. for a TrackMap plot
{"device":"${DEVICE}","itf":"CAN","chn":"CH2","db":"canmod-gps","signal":"(Latitude|Longitude)"}
```

#### Bundle queries for multiple panels 
When displaying multiple panels in your dashboard, it is critical to setup all queries in a single panel (as in our template). All other panels can then be set up to refer to the original panel by setting the datasource as `-- Dashboard --`. For both the 'query panel' and 'referring panels' you can then use the `Transform` tab to `Filter data by query`. This allows you to specify which query should be displayed in which panel. The end result is that only 1 query is sent to the backend - which means that your CANedge log files are only processed once per update. 

<img src="https://canlogger1000.csselectronics.com/img/dashboard-query-bundling.jpg" width="679.455" height="226.477">

#### Set up Grafana Variables & Annotations
Grafana Variables allow users to use dropdowns to dynamically control what is displayed in certain panels. For details on how the Variables are defined, see the template dashboard under `Settings/Variables`.

Similarly, Annotations can be used to display when a new log file 'session' or 'split' occurs, as well as display the log file name. This makes it easy to identify the log files underlying a specific view - and then finding these via [CANcloud](https://canlogger.csselectronics.com/canedge-getting-started/transfer-data/server-tools/cancloud-intro/) or [TntDrive](https://canlogger.csselectronics.com/canedge-getting-started/transfer-data/server-tools/other-s3-tools/) for further processing.

<img src="https://canlogger1000.csselectronics.com/img/Grafana-Variables-Annotations.jpg" width="679.455" height="226.477">

----

## Pending tasks 
Below are a list of pending items:

- Optimize Flask/Waitress session management for stability
- Update guide for EC2 service deployment for stability (instead of tmux)
- Update guide for TLS-enabled EC2 deployment 
