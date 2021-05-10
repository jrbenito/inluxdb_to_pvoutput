# inluxdb_to_pvoutput

Query generation data from InfluxDB v2.0 and send it to pvoutput.org

## K8s Deployment

Create configuration file based one `pvoutput.conf.rename` and add it as a configMap to the Kubernetes

`kubectl -n pvoutput create configmap pvoutput-conf --from-file=./pvoutput.conf`

Create a deployment to run this image:

`kubectl -n pvoutput apply -f k8s-deployment.yaml`

## Build docker image

`docker build -t jrbenito/influx2pvoutput .`

`docker push jrbenito/influx2pvoutput`
