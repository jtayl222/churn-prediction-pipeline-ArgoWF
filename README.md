# here

```bash

kubectl apply -f pvc.yaml

kubectl -n argowf describe  pvc churn-data-pv

kubectl apply -f copy-file-pod.yaml

kubectl -n argowf exec -it copy-file-pod -- bash

kubectl cp  REPOS/churn-prediction-pipeline/data/WA_Fn-UseC_-Telco-Customer-Churn.csv  argowf/copy-file-pod:/mnt/churn-data

```
