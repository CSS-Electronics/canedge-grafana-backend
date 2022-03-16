# CANedge Grafana Backend - Visualize CAN/LIN Data in Dashboards

This project enables easy dashboard visualization of log files from the [CANedge](https://www.csselectronics.com/pages/can-bus-hardware-products) CAN/LIN data logger. 

Specifically, a light-weight backend app loads, DBC decodes and parses MDF log files from local disk or an S3 server. This is done 'on demand' in response to query requests sent from a [Grafana dashboard](https://grafana.com/) frontend by end users. 

**This project is currently in BETA - major changes will be made.**

![CAN Bus Grafana Dashboard](https://canlogger1000.csselectronics.com/img/can-bus-telematics-dashboard-template.png)


## Backend vs. Writer
We provide two options for integrating your CANedge data with Grafana dashboards:

The [CANedge Grafana Backend](https://github.com/CSS-Electronics/canedge-grafana-backend) app only processes data 'when needed' by an end user - and requires no database. It is ideal when you have large amounts of data - as you only process the data you need to visualize. 

In contrast, the [CANedge InfluxDB Writer](https://github.com/CSS-Electronics/canedge-influxdb-writer) requires that you process relevant data in advance (e.g. periodically or on-file-upload) and write the decoded data to a database. It is ideal if the dashboard loading speed is critical - but with the downside that large amounts of data is processed & stored (at a cost) without being used.

For details incl. 'pros & cons', see our [intro to telematics dashboards](https://www.csselectronics.com/pages/telematics-dashboard-open-source).

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

Note: We strongly recommend to test the local deployment with our sample data as the first step.

Once you've made that work, you can start the backend with your own data/DBC files as per step 3.

### 1: Deploy the integration locally on your PC

A local PC deployment is ideal for testing, as well as parsing data from local disk or MinIO S3.

- [Watch the step-by-step video](https://canlogger1000.csselectronics.com/img/canedge-grafana-backend-local_v2.mp4)

#### Deploy the backend app locally
- Install Python 3.7 for Windows ([32 bit](https://www.python.org/ftp/python/3.7.9/python-3.7.9.exe)/[64 bit](https://www.python.org/ftp/python/3.7.9/python-3.7.9-amd64.exe)) or [Linux](https://www.python.org/downloads/release/python-379/) (_enable 'Add to PATH'_)
- Download this project as a zip via the green button and unzip it 
- Open the folder with the `requirements.txt` file, open your [command prompt](https://www.youtube.com/watch?v=bgSSJQolR0E&t=47s) and enter below:

##### Windows 
```
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
python canedge_datasource_cli.py "file:///%cd%/LOG" --port 8080
```

##### Linux 
```
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
python3 canedge_datasource_cli.py file:///$PWD/LOG --port 8080
```

#### Set up Grafana locally
- [Install Grafana locally](https://grafana.com/grafana/download?platform=windows) and enter `http://localhost:3000` in your browser to open Grafana
- In `Configuration/Plugins` install `SimpleJson` and `TrackMap`
- In `Configuration/DataSources` select `Add datasource` and `SimpleJson` and set it as the 'default'
- Enter the URL `http://localhost:8080/`, hit `Save & test` and verify that it works
- In `Dashboards/Browse` click `Import` and load the `dashboard-template.json` from this repo 

You should now see the sample data visualized when you open the imported dashboard in Grafana. If you later need to re-start the backend, remember to 'activate' the virtual environment first. If you aim to work with data stored on your PC, you can look into loading your own data (step 3) and optionally port forwarding (step 5). If you aim to load data from AWS S3, proceed to step 2.


### 2: Deploy the integration on AWS EC2 & Grafana Cloud
An [AWS EC2](https://aws.amazon.com/ec2/) instance is ideal for parsing data from AWS S3.

- [Watch the step-by-step video](https://canlogger1000.csselectronics.com/img/canedge-grafana-backend-aws-ec2-cloud.mp4)

#### Deploy the backend app on AWS EC2 

- Login to AWS, search for `EC2/Instances` and click `Launch instances`
- Select `Ubuntu Server 20.04 LTS (HVM), SSD Volume Type`, `t3.small` and proceed
- In `Step 6`, click `Add Rule/Custom TCP Rule` and set `Port Range` to `8080`
- Launch the instance, then create & store your credentials (we will not use them for now) 
- Wait a few minutes, then click on your instance and note your `Public IPv4 address`
- Click `Connect/Connect` to enter the GUI console, then enter the following:

```
sudo apt update && sudo apt install python3 python3-pip python3-venv tmux 
git clone https://github.com/CSS-Electronics/canedge-grafana-backend.git
cd canedge-grafana-backend
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
tmux
python3 canedge_datasource_cli.py file:///$PWD/LOG --port 8080
```

#### Set up Grafana Cloud
- [Set up](https://grafana.com/auth/sign-up/create-user) a free Grafana Cloud account and log in
- In `Configuration/Plugins` install `SimpleJson` and `TrackMap` (log out and in again)
- In `Configuration/DataSources` select `Add datasource` and `SimpleJson` and set it as the 'default'
- Replace your datasource URL with the `http://[IP]:[port]` endpoint and click `Save & test` 

You should now see the sample data visualized in your imported dashboard. In the AWS EC2 console you can press `ctrl + B` then `D` to de-attach from the session, allowing it to run even when you close the GUI console.

See also step 3 on loading your AWS S3 data and step 5 on deploying the app as a service for production.


-----

### 3: Load your own log files & DBC files

#### Parse data from local disk 
If you want to work with data from your local disk (e.g. a CANedge1 SD card), you must ensure that your data folder is structured similarly to the sample data `LOG/` folder. Your DBC file(s) must be placed in the folder root, while log files must be placed in the `[folder/bucket]/[device_id]/[session]/[split].MF4` structure.

#### Parse data from S3

To parse data from S3 (MinIO, AWS, ...), add your DBC file(s) to the root of your S3 bucket. Next, use below syntax to start the backend (use `python3` on EC2):

```
python canedge_datasource_cli.py [endpoint] --port 8080 --s3_ak [access_key] --s3_sk [secret_key] --s3_bucket [bucket]
```

- AWS S3 endpoint example: `https://s3.eu-central-1.amazonaws.com`
- MinIO S3 endpoint example: `http://192.168.192.1:9000`

#### Regarding DBC files 
All DBC files placed in the `[folder/bucket]/` root will be loaded and available for decoding (see the `LOG/` folder example). If you need to use multiple DBC files, consider merging & trimming these for performance.

----

### 4: Customize your Grafana dashboard

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
Grafana Variables allow users to dynamically control what is displayed in certain panels via dropdowns. For details on how the Variables are defined, see the template dashboard under `Settings/Variables`.

Similarly, Annotations can be used to display when a new log file 'session' or 'split' occurs, as well as display the log file name. This makes it easy to identify the log files underlying a specific view - and then finding these via [CANcloud](https://canlogger.csselectronics.com/canedge-getting-started/transfer-data/server-tools/cancloud-intro/) or [TntDrive](https://canlogger.csselectronics.com/canedge-getting-started/transfer-data/server-tools/other-s3-tools/) for further processing.

<img src="https://canlogger1000.csselectronics.com/img/Grafana-Variables-Annotations.jpg" width="679.455" height="226.477">

#### Regarding performance
Using the 'zoom out' button repeatedly will currently generate a queue of requests, each of which will be processed by the backend. Until this is optimized, we recommend to make a single request a time - e.g. by using the time period selector instead of the 'zoom out' button. 

Also, loading speed increases when displaying long time periods (as the data for the period is processed in real-time).

----

### 5: Move to a production setup (EC2)

##### Managing your EC2 tmux session

Below commands are useful in managing your `tmux` session while you're still testing your deployment.

- `tmux`: Start a session
- `tmux ls`: List sessions 
- `tmux attach`: Re-attach to session
- `tmux kill-session`: Stop session

#### Deploy your app as an EC2 service for production

The above setup is suitable for development & testing. Once you're ready to deploy for production, you may prefer to set up a service. This ensures that your app automatically restarts after an instance reboot or a crash. To set it up as a service, follow the below steps:

- Ensure you've followed the previous EC2 steps incl. the virtual environment
- Update the `ExecStart` line in the `canedge_grafana_backend.service` 'unit file' with your S3 details
- Upload the modified file to get a public URL
- In your EC2 instance, use below commands to deploy the file

```
sudo wget -N [your_file_url]
sudo cp canedge_grafana_backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start canedge_grafana_backend
sudo systemctl enable canedge_grafana_backend
sudo journalctl -f -u canedge_grafana_backend
```

The service should now be deployed, which you can verify via the console output. If you need to make updates to your unit file, simply repeat the above. You can stop the service via `sudo systemctl stop [service]`.

#### Regarding EC2 costs
You can find details on AWS EC2 pricing [here](https://aws.amazon.com/ec2/pricing/on-demand/). A `t3.small` instance typically costs ~0.02$/hour (~15-20$/month). We recommend that you monitor usage during your tests early on to ensure that no unexpected cost developments occur. Note also that you do not pay for the data transfer from S3 into EC2 if deployed within the same region. 

#### Regarding public EC2 IP 
Note that rebooting your EC2 instance will imply that your endpoint IP is changed - and thus you'll need to update your datasource. There are methods to set a fixed IP, though not in scope of this README. 


#### Port forwarding a local deployment

If you want to access the data remotely, you can set up port forwarding. Below we outline how to port forward the backend app for use as a datasource in Grafana Cloud - but you could of course also directly port forward your local Grafana dashboard directly via port `3000`. 

- Set up [port forwarding](https://portforward.com/) on your WiFi router for port `8080`
- Run the app again (you may need to allow access via your firewall)
- Find your [public IP](https://www.whatismyip.com/) to get your endpoint as: `http://[IP]:[port]` (e.g. `http://5.105.117.49:8080/`)
- Verify that you see an `OK` when opening the endpoint in your browser
- In Grafana, add your endpoint URL, click `Save & test` and verify that your dashboard displays the data

----

### Pending tasks 
Below are a list of pending items:

- Optimize Flask/Waitress session management for stability
- Improve performance for multiple DBC files
- Update guide for EC2 service deployment for stability (instead of tmux)
- Update code/guide for TLS-enabled deployment 
- Provide guidance on how to best scale the app for multiple front-end users 
- Determine if using `Browser` in SimpleJson datasource improves performance (requires TLS)
