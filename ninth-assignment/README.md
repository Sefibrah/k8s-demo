# Ninth Assignment

## Local Deployment

```shell
kind create cluster --name ceng459-cluster

kubectl config use-context kind-ceng459-cluster

docker build -t sefibra/ceng459-ninth-assignment:latest .

kind load docker-image sefibra/ceng459-ninth-assignment:latest --name ceng459-cluster

kubectl apply -f deployment.yaml

# kubectl port-forward deployment/ceng459-ninth-assignment 8080:80
```

## GKE Deployment

In this assignment, I have ran all of the steps below to successfuly complete the assignment. Here are some variables to keep in mind as well:

```
PROJECT_ID = 'swift-terra-446115-q5'
```

And here are the steps right below:

```shell
docker build . -t sefibra/ceng459-ninth-assignment:latest

docker push sefibra/ceng459-ninth-assignment:latest

gcloud auth login

gcloud config set project swift-terra-446115-q5 

gcloud container clusters create ceng459-ninth-assignment --zone europe-central2 --num-nodes=1 --machine-type=e2-micro

gcloud components install gke-gcloud-auth-plugin

gcloud container clusters get-credentials ceng459-ninth-assignment --region=europe-central2

kubectl create deployment ceng459-ninth-assignment-deployment --image sefibra/ceng459-ninth-assignment:latest 

# returned:  deployment.apps/ceng459-ninth-assignment-deployment created  

# kubectl apply -f deployment.yaml
# returned: service/py-application-cpu created
# returned: deployment.apps/py-application-cpu created

kubectl get deployment

# returned:
## NAME                                  READY   UP-TO-DATE   AVAILABLE   AGE
## ceng459-ninth-assignment-deployment   1/1     1            1           25s

kubectl expose deployment ceng459-ninth-assignment-deployment --type=LoadBalancer --port 8080 --target-port 80

# returned: service/ceng459-ninth-assignment-deployment exposed

kubectl get services

# returned:
## NAME                                  TYPE           CLUSTER-IP      EXTERNAL-IP      PORT(S)          AGE
## ceng459-ninth-assignment-deployment   LoadBalancer   34.118.232.13   34.116.174.115   8080:31985/TCP   39s
## kubernetes                            ClusterIP      34.118.224.1    <none>           443/TCP          15m
```

Then we take the `ceng459-ninth-assignment-deployment` EXTERNAL-IP address, combine it with the PORT of `8080` and by pasting that (`http://34.116.174.115:8080/`) in the URL we should get our simple python application running!