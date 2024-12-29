# Step by step

```shell
brew install minikube

minikube start --driver=docker

docker build -t sefibra/k8s-scaling-demo:v1 .

docker push sefibra/k8s-scaling-demo:v1

# make a deployment.yaml file... then run:

kubectl apply -f deployment.yaml

# then expose the deployment:

kubectl expose deployment scaling-demo --type=NodePort --port=5000

minikube service scaling-demo --url

# install `hey` for load testing

brew install hey

# run the load test

hey -z 30s -c 5 http://127.0.0.1:50740 

# scale the deployment

kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

kubectl autoscale deployment scaling-demo --cpu-percent=50 --min=1 --max=5

# run the load test again, you should see the number of pods increase

hey -z 60s -c 20 http://127.0.0.1:50740

brew install podman

# install Go from https://go.dev/dl/ , I installed go1.23.4.darwin-amd64.pkg ...

brew install kind
# OR USE THIS
go install sigs.k8s.io/kind@latest


```

Provisioning Infrastructure for your FE and BE applications can become tedious, and slow everyone around you whilst doing this manually and not to mention the human error that can occur. So autoscaling is a great way to manage this, and Kubernetes provides a way to do this with the Horizontal Pod Autoscaler.

Using .yaml files, we can define the desired state of our application, and Kubernetes will manage the rest. This .yaml file will be provided to the FE and BE developers to deploy their applications, and the Kubernetes cluster will manage the rest.

And nobody has to constantly provision infrastructure, and the applications will scale up and down based on the load.

.yaml files allow you to define many things such as what container image should it deploy, what ports should it export, what health probes to monitor, any configs, any secrets that may be required, resource requests and limits, as well as the number of replicas.

Hardcoding the number of replicas is OK in the beginning. But let's say that the demand of your application grows overtime... You might need 8 pods to cover the demand during the day, but only 2 pods during the night. This is where the Horizontal Pod Autoscaler comes in.

Let's demonstrate this using `kind`, which stands for Kubernetes IN Docker, (and `minikube`???) to create a Kubernetes cluster, and deploy a simple application that we can scale up and down.

We run:

```shell
https://hub.docker.com/r/kindest/node/tags

kind create cluster --name hpa --image kindest/node:v1.29.12
```

On my machine, I've allocated 6 CPU cores out of my 16 CPU cores to Docker, so my kubernetes cluster will have 6 CPU cores to work with.

To demonstrate this, I have a simple Go lang application that will simulate CPU consumption. I also have a `deployment.yaml` file specifying to Kubernetes how many replicas will it run, what container will it run, what port should it expose, resource requests and limits.

Then to run this `deployment.yaml`, we `cd` into it and run `kubectl apply -f deployment.yaml`.

# Traffic simulation

Now to simulate some traffic, we can use `hey` to simulate some traffic. We will make it so that our app really struggles and makes users have a hard time. Here's the command to do so:

```shell
hey -z 60s -c 100 http://<your-app-url>
```

OR

```shell
docker build . -t sefibra/application-cpu:v1.0.0
docker push sefibra/application-cpu:v1.0.0
kubectl apply -f deployment.yaml
```

```shell
kubectl apply -f traffic-generator.yaml
kubectl exec -it traffic-generator sh
# inside of the traffic-generator run: 
apk add --no-cache wrk
# and also we run
wrk -c 5 -t 5 -d 99999 -H "Connection: Close" http://py-application-cpu
```

Typically, we can use Prometheus to be alerted about high traffic. These alerts allow us HUMANS to act accordingly. But how can Kubernetes get this data, and have it act accordingly instead?

The answer? Metrics Server. 

# Metrics Server

Metrics server runs in the kube-system namespace, and it monitors key metrics like CPU and Memory of Pods and Nodes. It gathers this information at an interval and it gives it back to the API, which means that we can build pipelines around these metrics, like auto scalers.

Now, Kubernetes has this component called Metrics Server which is built and maintained by the OS community.

https://github.com/kubernetes-sigs/metrics-server

In our case, we are using `v1.29.12`, which is greater than the 2 `v1.19` thresholds in the docs, we can get our hands on the latest Metrics Server. To do this, we simply go to the Releases section of their GitHub repo, go to `v0.7.2` because it is the latest one, and download the `components.yaml` file

# Horizontal Pod Autoscaler

Let's rename the `components.yaml` into `metricserver-0.7.2.yaml`.

In the `metricserver-0.7.2.yaml` file, there's an `args` section, in which we must add these two arguments to make this demo work in our local testing environment:

```yaml
--kubelet-insecure-tls
--kubelet-preferred-address-types="InternalIP"
```

Now to run this Metrics Server, we run the following command:

```shell
kubectl -n kube-system apply -f metricserver-0.7.2.yaml
```

Now we can check out our newly made Metrics Server by running:

```shell
kubectl -n kube-system get pods
```

If it gives you something like this:
```shell
NAME                                        READY   STATUS    RESTARTS      AGE
metrics-server-5b94f5b9f6-mtwcx             0/1     Running   0             81s
metrics-server-d584884fc-db9p4              0/1     Pending   0             3s
```

Then make sure that your Docker has enough Memory or CPU to run this Metrics Server. If you're running on a Mac, you can go to Docker Desktop -> Preferences -> Resources -> Advanced and increase the Memory and CPU.

Then it should look like this:

```shell
NAME                                        READY   STATUS    RESTARTS      AGE
metrics-server-5b94f5b9f6-mtwcx             1/1     Running   1 (20m ago)   23m
```

And just to get some brief overviews of our pods and nodes, we can run:

```shell
kubectl top pods

# which gives us

NAME                             CPU(cores)   MEMORY(bytes)   
application-cpu-8d585448-qfj42   2000m        13Mi   # -> it is using 2000 mili cores, and 13 Mi of memory
traffic-generator                314m         12Mi    
```

And to see our top nodes, we can run:

```shell
kubectl top nodes

# which gives us

NAME                CPU(cores)   CPU%   MEMORY(bytes)   MEMORY%   
hpa-control-plane   2974m        37%    839Mi           14%    
```

So now that Kubernetes knows exactly how much CPU and Memory our application is using, as well as how much CPU and Memory our nodes are using, as well as how much CPU and Memory did we allocate to each of our pods, this allows us to do some cool things.

Now Kubernetes knows we have a 8-core machine. 1 core equals 1000 mili cores. So if we have 8 cores, we have 8000 mili cores on this node. Kubernetes knows that we expect each pod to use 500 mili cores... defined in our `.yaml` file. Dividing 8000 by 500, the scheduler knows it's able to roughly 16 pods onto this machine. We can visualise each pod almost like a micro virtual machine that has 500 mili cores. Now because of the high traffic load we see at the top, our pod is currently sitting at 2000 mili cores, and technically speaking, it is running at 400% CPU usage. Now adding more pods would allow the CPU usage to spread out more evenly, and the CPU usage would drop down to roughly 100% for each pod. The more pods we add, the better. Each pod will start to use more or less the same amount of CPU as we've allocated, and this is good! It is important the allocated CPU is close enough to the (arbitrarily) desired optimal CPU usage for that workload.

# Manual Pod Scaling

Since we figured out that our singular pod is basically at 400% CPU usage, this roughly translates to highly dissatisfied customers, high error rates, and a bad user experience. We can fix this by adding more pods.

So let's start by finding out where is our sweet spot? We can do this by running the following command:

```shell
kubectl scale deploy/application-cpu --replicas 2
```

And then we can checkout the CPU usage of our pods:

```shell
kubectl top pods
```

It may take some time to see changes, but once it's done, you should see something like this:

```shell
NAME                             CPU(cores)   MEMORY(bytes)   
application-cpu-8d585448-h4c4k   1767m        6Mi             
application-cpu-8d585448-qfj42   1849m        13Mi            
traffic-generator                322m         13Mi  
```

As you can see, the CPU usage for each pod is around 1800 mili cores, which is much better than the 2000 mili cores we had before. This is because we have 2 pods now, and the CPU usage is spread out more evenly, i.e. from 400% to 360%. But this is not good enough, we need to add more pods.

Let's try 4 replicas:

```shell
kubectl scale deploy/application-cpu --replicas 4

# we wait for a bit for the pods to instantiate

kubectl top pods
```

And you should see something like this:

```shell
NAME                             CPU(cores)   MEMORY(bytes)   
application-cpu-8d585448-6h9fj   842m         5Mi             
application-cpu-8d585448-h4c4k   866m         5Mi             
application-cpu-8d585448-ncphj   871m         4Mi             
application-cpu-8d585448-qfj42   864m         12Mi   
```

A much better CPU usage, we jumped from ~360% per pod to ~170% per pod. But we can do better. Let's try 7 replicas:

```shell
kubectl scale deploy/application-cpu --replicas 7

# we wait for a bit for the pods to instantiate

kubectl top pods
```

And you should see something like this:

```shell
NAME                             CPU(cores)   MEMORY(bytes)   
application-cpu-8d585448-5dtzm   425m         7Mi             
application-cpu-8d585448-6h9fj   415m         4Mi             
application-cpu-8d585448-h4c4k   421m         4Mi             
application-cpu-8d585448-ncphj   403m         4Mi             
application-cpu-8d585448-qfj42   417m         11Mi            
application-cpu-8d585448-rlzjv   435m         5Mi             
application-cpu-8d585448-v45z2   429m         5Mi   
```

As you can see, now each pod is running at roughly ~85% CPU usage, which is much better than the ~170% CPU usage we had before. This is because we have 7 pods now, and the CPU usage is spread out more evenly. We see that each pod is below the 500 mili core threshold that we've requested in our `deployment.yaml` file. This is the sweet spot for our application.

Now every workload is going to be different... So it's important to take a look at your own metrics like latency, traffic, errors, and saturation to make sure to find your sweet spot for setting your request value of CPU correctly.

In this demo, the sweet spot is around 500 mili cores. You need to find your own sweet spot to make sure you're utilising your CPU as much as possible!

But this was all done manually! We don't want to do this manually, we want Kubernetes to do this for us. This is where the Horizontal Pod Autoscaler comes in.

# Horizontal Pod Autoscaler

It is important to know your reasons for your sweet spot, and it's important to understand the impact of setting the right resource requests and limits for the CPU and memory...

Now let's look at how we can scale up our application automatically by taking these values from our `deployment.yaml` file and by looking at the metrics from the Metrics Server.

Let's first scale down our application back to 1 pod:

```shell
kubectl scale deploy/application-cpu --replicas 1
```

Here's how our pods look like now:

```shell
NAME                             CPU(cores)   MEMORY(bytes)   
application-cpu-8d585448-qfj42   1999m        12Mi    
```

As you can see, we are back at 2000 mili cores, which is not good. We need to scale up our application automatically.

We can do this by running the following command:

```shell
kubectl autoscale deploy/application-cpu --cpu-percent=95 --min=1 --max=10

# to remove autoscaling run
kubectl delete hpa application-cpu
```

This command tells Kubernetes to autoscale our application based on the CPU usage. If the CPU usage is above 95%, Kubernetes will add more pods, and if the CPU usage is below 95%, Kubernetes will remove pods.

Now when we run `kubectl get pods`, we should see something like this:

```shell
NAME                             READY   STATUS    RESTARTS   AGE
application-cpu-8d585448-9vv7r   1/1     Running   0          50s
application-cpu-8d585448-btch7   1/1     Running   0          50s
application-cpu-8d585448-p96t6   1/1     Running   0          50s
application-cpu-8d585448-pjdmk   1/1     Running   0          5s
application-cpu-8d585448-qfj42   1/1     Running   0          67m
application-cpu-8d585448-wjw78   1/1     Running   0          35s
```

We downscaled manually to 1 pod, and now the HPA has autoscaled our app back to 6 pods. Let's look at the CPU usage of our pods. We do this by running `kubectl top pods`:

```shell
kubectl top pods

kubectl get hpa/application-cpu  -owide

kubectl describe hpa/application-cpu
```

```shell
NAME                             CPU(cores)   MEMORY(bytes)   
application-cpu-8d585448-9vv7r   443m         5Mi             
application-cpu-8d585448-btch7   470m         5Mi             
application-cpu-8d585448-btlp9   446m         7Mi             
application-cpu-8d585448-p96t6   475m         4Mi             
application-cpu-8d585448-pjdmk   451m         7Mi             
application-cpu-8d585448-pzmqt   450m         5Mi             
application-cpu-8d585448-qfj42   447m         11Mi            
application-cpu-8d585448-wjw78   443m         4Mi   
```

It looks like that it autoscaled even more during my talk to 8 pods. This was done automatically! Can you imagine the time and effort saved by not having to do this manually?

Now let's look at a final metric by running `kubectl get hpa/application-cpu  -owide`:

```shell
NAME              REFERENCE                    TARGETS   MINPODS   MAXPODS   REPLICAS   AGE
application-cpu   Deployment/application-cpu   77%/95%   1         10        8          4m29s
```

We see that because of our artifical high traffic, we now have 8 pods running, and the CPU usage is at 77%, which is below the 95% threshold we've set. This is good! This means that our application is running smoothly, and we have enough pods to handle the traffic.

We can also take a look at the reasons why did the HPA decide to scale up or down by running `kubectl describe hpa/application-cpu`:

```shell
Name:                                                  application-cpu
Namespace:                                             default
Labels:                                                <none>
Annotations:                                           <none>
CreationTimestamp:                                     Thu, 19 Dec 2024 10:36:33 +0300
Reference:                                             Deployment/application-cpu
Metrics:                                               ( current / target )
  resource cpu on pods  (as a percentage of request):  89% (449m) / 95%
Min replicas:                                          1
Max replicas:                                          10
Deployment pods:                                       8 current / 8 desired
Conditions:
  Type            Status  Reason              Message
  ----            ------  ------              -------
  AbleToScale     True    ReadyForNewScale    recommended size matches current size
  ScalingActive   True    ValidMetricFound    the HPA was able to successfully calculate a replica count from cpu resource utilization (percentage of request)
  ScalingLimited  False   DesiredWithinRange  the desired count is within the acceptable range
Events:
  Type    Reason             Age    From                       Message
  ----    ------             ----   ----                       -------
  Normal  SuccessfulRescale  6m35s  horizontal-pod-autoscaler  New size: 4; reason: cpu resource utilization (percentage of request) above target
  Normal  SuccessfulRescale  6m20s  horizontal-pod-autoscaler  New size: 5; reason:
  Normal  SuccessfulRescale  5m50s  horizontal-pod-autoscaler  New size: 6; reason: cpu resource utilization (percentage of request) above target
  Normal  SuccessfulRescale  5m20s  horizontal-pod-autoscaler  New size: 8; reason: cpu resource utilization (percentage of request) above target
```

We see how our HPA is making decisions in the Events table...

HPA is also smart enough to wait for a few minutes before scaling down, to make sure that the traffic is not just a spike. This is why we see the `SuccessfulRescale` events happening every 5 minutes or so.

Now if we don't like the HPA's default behaviour configurations, we can go ahead and configure it manually to fit our needs even more!

By reading the docs at https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#configurable-scaling-behavior we can see how we can configure the HPA to fit our needs. You can see that the docs talk about some Policies, which you can configure to fit your needs.